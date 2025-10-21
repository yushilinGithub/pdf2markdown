# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
decoder

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""

from typing import Optional, Union, Tuple
from loguru import logger

import torch
from transformers import PreTrainedModel, VisionEncoderDecoderConfig, PretrainedConfig
from transformers.modeling_outputs import Seq2SeqLMOutput, BaseModelOutput
from transformers.models.vision_encoder_decoder.modeling_vision_encoder_decoder import shift_tokens_right
from src.rock.model.recognition.encoder import DonutSwinModel
from src.rock.model.recognition.decoder import SuryaOCRDecoder, SuryaOCRTextEncoder


class OCREncoderDecoderModel(PreTrainedModel):
    """ OCR Encoder Decoder Model"""
    config_class = VisionEncoderDecoderConfig
    base_model_prefix = "vision_encoder_decoder"
    main_input_name = "pixel_values"
    supports_gradient_checkpointing = True
    _supports_param_buffer_assignment = False

    def __init__(
        self,
        config: Optional[PretrainedConfig] = None,
        encoder: Optional[PreTrainedModel] = None,
        decoder: Optional[PreTrainedModel] = None,
        text_encoder: Optional[PreTrainedModel] = None,
    ):   
        """ initialize the model """
        # initialize with config
        # make sure input & output embeddings is not tied
        config.tie_word_embeddings = False
        config.decoder.tie_word_embeddings = False
        super().__init__(config)

        if encoder is None:
            encoder = DonutSwinModel(config.encoder)

        if decoder is None:
            decoder = SuryaOCRDecoder(config.decoder, attn_implementation=config._attn_implementation)

        if text_encoder is None:
            text_encoder = SuryaOCRTextEncoder(config.text_encoder, attn_implementation=config._attn_implementation)

        self.encoder = encoder
        self.decoder = decoder
        self.text_encoder = text_encoder

        # make sure that the individual model's config refers to the shared config
        # so that the updates to the config will be synced
        self.encoder.config = self.config.encoder
        self.decoder.config = self.config.decoder
        self.text_encoder.config = self.config.text_encoder

    def get_encoder(self):
        """ get encoder """
        return self.encoder

    def get_decoder(self):
        """ get decoder """
        return self.decoder

    def get_output_embeddings(self):
        """ get output embeddings """
        return self.decoder.get_output_embeddings()

    def set_output_embeddings(self, new_embeddings):
        """ set output embeddings """
        return self.decoder.set_output_embeddings(new_embeddings)

    def forward(
        self,
        pixel_values: Optional[torch.FloatTensor] = None,
        decoder_input_ids: Optional[torch.LongTensor] = None,
        decoder_cache_position: Optional[torch.LongTensor] = None,
        decoder_attention_mask: Optional[torch.BoolTensor] = None,
        encoder_outputs: Optional[Tuple[torch.FloatTensor]] = None,
        use_cache: Optional[bool] = None,
        **kwargs,
    ) -> Union[Tuple[torch.FloatTensor], Seq2SeqLMOutput]:
        """ forward pass """

        kwargs_encoder = {argument: value for argument, value in kwargs.items() if not argument.startswith("decoder_")}

        kwargs_decoder = {
            argument[len("decoder_") :]: value for argument, value in kwargs.items() if argument.startswith("decoder_")
        }

        if encoder_outputs is None:
            if pixel_values is None:
                raise ValueError("You have to specify pixel_values")

            encoder_outputs = self.encoder(
                pixel_values=pixel_values,
                **kwargs_encoder,
            )
        elif isinstance(encoder_outputs, tuple):
            encoder_outputs = BaseModelOutput(*encoder_outputs)

        encoder_hidden_states = encoder_outputs[0]

        # optionally project encoder_hidden_states
        logger.info("encoder_hidden_states", encoder_hidden_states.shape)
        if (
            self.encoder.config.hidden_size != self.decoder.config.hidden_size
            and self.decoder.config.cross_attention_hidden_size is None
        ):
            encoder_hidden_states = self.enc_to_dec_proj(encoder_hidden_states)
            logger.info("encoder_hidden_states.shape", encoder_hidden_states.shape)
        # else:
        encoder_attention_mask = None

        # Decode
        decoder_outputs = self.decoder(
            input_ids=decoder_input_ids,
            cache_position=decoder_cache_position,
            attention_mask=decoder_attention_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=use_cache,
            **kwargs_decoder,
        )

        return Seq2SeqLMOutput(
            logits=decoder_outputs.logits,
            decoder_hidden_states=decoder_outputs.hidden_states,
            encoder_last_hidden_state=encoder_outputs.last_hidden_state
        )

    def prepare_decoder_input_ids_from_labels(self, labels: torch.Tensor):
        """ prepare decoder input ids from labels """
        return shift_tokens_right(labels, self.config.pad_token_id, self.config.decoder_start_token_id)

    def prepare_inputs_for_generation(
        self, input_ids, past_key_values=None, attention_mask=None, use_cache=None, encoder_outputs=None, **kwargs
    ):
        """ prepare inputs for generation """
        decoder_inputs = self.decoder.prepare_inputs_for_generation(input_ids, past_key_values=past_key_values)
        decoder_attention_mask = decoder_inputs["attention_mask"] if "attention_mask" in decoder_inputs else None
        input_dict = {
            "attention_mask": attention_mask,
            "decoder_attention_mask": decoder_attention_mask,
            "decoder_input_ids": decoder_inputs["input_ids"],
            "encoder_outputs": encoder_outputs,
            "past_key_values": decoder_inputs["past_key_values"],
            "use_cache": use_cache,
        }
        return input_dict

    def resize_token_embeddings(self, *args, **kwargs):
        """ resize token embeddings """
        raise NotImplementedError(
            "Resizing the embedding layers via the VisionEncoderDecoderModel directly is not supported.Please use the"
            " respective methods of the wrapped decoder object (model.decoder.resize_token_embeddings(...))"
        )

    def _reorder_cache(self, past_key_values, beam_idx):
        """ reorder cache """
        # apply decoder cache reordering here
        return self.decoder._reorder_cache(past_key_values, beam_idx)