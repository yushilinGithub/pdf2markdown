# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
decoder

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


import warnings

import torch
from loguru import logger


from typing import List, Optional, Tuple
from src.rock.model.recognition.encoderdecoder import OCREncoderDecoderModel
from src.rock.model.recognition.config import DonutSwinConfig, \
                                SuryaOCRConfig, SuryaOCRDecoderConfig, \
                                 SuryaOCRTextEncoderConfig
from src.rock.model.recognition.encoder import DonutSwinModel
from src.rock.model.recognition.decoder import SuryaOCRDecoder, SuryaOCRTextEncoder
from src.rock.settings import settings

if not settings.ENABLE_EFFICIENT_ATTENTION:
    logger.info("Efficient attention is disabled. This will use significantly more VRAM.")
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_flash_sdp(True)
    torch.backends.cuda.enable_math_sdp(True)


def load_model(checkpoint=settings.RECOGNITION_MODEL_CHECKPOINT, \
                    device=settings.TORCH_DEVICE_MODEL, dtype=settings.MODEL_DTYPE):
    """ Load the model from the checkpoint"""
    config = SuryaOCRConfig.from_pretrained(checkpoint)
    decoder_config = config.decoder
    decoder = SuryaOCRDecoderConfig(**decoder_config)
    config.decoder = decoder

    encoder_config = config.encoder
    encoder = DonutSwinConfig(**encoder_config)
    config.encoder = encoder

    text_encoder_config = config.text_encoder
    text_encoder = SuryaOCRTextEncoderConfig(**text_encoder_config)
    config.text_encoder = text_encoder

    model = OCREncoderDecoderModel.from_pretrained(checkpoint, config=config, torch_dtype=dtype)

    assert isinstance(model.decoder, SuryaOCRDecoder)
    assert isinstance(model.encoder, DonutSwinModel)
    assert isinstance(model.text_encoder, SuryaOCRTextEncoder)

    model = model.to(device)
    model = model.eval()

    logger.info(f"Loaded recognition model {checkpoint} on device {device} with dtype {dtype}")
    return model