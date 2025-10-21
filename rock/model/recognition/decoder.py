# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
decoder

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

import torch
import torch.utils.checkpoint
from torch import nn
from transformers.utils import ModelOutput

from src.rock.model.recognition.config import SuryaOCRDecoderConfig, SuryaOCRTextEncoderConfig
from transformers import PreTrainedModel
from transformers.activations import ACT2FN
from transformers.modeling_attn_mask_utils import AttentionMaskConverter
from transformers.modeling_outputs import BaseModelOutputWithNoAttention, CausalLMOutput
from transformers.pytorch_utils import ALL_LAYERNORM_LAYERS

from src.rock.settings import settings

_MAX_SQRT_GRADIENT = 1000.0


@dataclass
class OCRModelOutput(ModelOutput):
    """ocr model output"""
    logits: torch.Tensor
    aux_logits: torch.Tensor | None = None
    hidden_states: torch.Tensor | None = None


class SuryaOCRDecoderRMSNorm(nn.Module):
    """surya ocr decoder rms norm"""
    def __init__(self, dim: int, eps: float = 1e-6):
        """init"""
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.zeros(dim))

    def _norm(self, x):
        """norm"""
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x):
        """forward"""
        output = self._norm(x.float())
        # Llama does x.to(float16) * w whilst SuryaOCRDecoder is (x * w).to(float16)
        # See https://github.com/huggingface/transformers/pull/29402
        output = output * (1.0 + self.weight.float())
        return output.type_as(x)

    def extra_repr(self):
        """extra repr"""
        return f"{tuple(self.weight.shape)}, eps={self.eps}"


ALL_LAYERNORM_LAYERS.append(SuryaOCRDecoderRMSNorm)


class SuryaOCRDecoderRotaryEmbedding(nn.Module):
    """surya ocr decoder rotary embedding"""
    def __init__(self, dim, base=10000, device=None):
        """init"""
        super().__init__()
        self.dim = dim
        self.base = base
        inv_freq = 1.0 / (self.base ** (torch.arange(0, self.dim, 2, dtype=torch.int64).float() / self.dim))
        self.register_buffer("inv_freq", tensor=inv_freq, persistent=False)

    @torch.no_grad()
    # Copied from transformers.models.gemma.modeling_gemma.GemmaRotaryEmbedding.forward with Gemma->SuryaOCRDecoder
    def forward(self, x, position_ids, seq_len=None):
        """forward"""
        # x: [bs, num_attention_heads, seq_len, head_size]
        self.inv_freq.to(x.device)
        inv_freq_expanded = self.inv_freq[None, :, None].float().expand(position_ids.shape[0], -1, 1)
        position_ids_expanded = position_ids[:, None, :].float()

        freqs = (inv_freq_expanded.float() @ position_ids_expanded.float()).transpose(1, 2)
        emb = torch.cat((freqs, freqs), dim=-1)
        cos = emb.cos()
        sin = emb.sin()
        return cos.to(dtype=x.dtype), sin.to(dtype=x.dtype)


# Copied from transformers.models.llama.modeling_llama.rotate_half
def rotate_half(x):
    """Rotates half the hidden dims of the input."""
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)


# Copied from transformers.models.llama.modeling_llama.apply_rotary_pos_emb
def apply_rotary_pos_emb(q, k, cos, sin, unsqueeze_dim=1):
    """Applies Rotary Position Embedding to the query and key tensors.

    Args:
        q (`torch.Tensor`): The query tensor.
        k (`torch.Tensor`): The key tensor.
        cos (`torch.Tensor`): The cosine part of the rotary embedding.
        sin (`torch.Tensor`): The sine part of the rotary embedding.
        unsqueeze_dim (`int`, *optional*, defaults to 1):
            The 'unsqueeze_dim' argument specifies the dimension along which to unsqueeze cos[position_ids] and
            sin[position_ids] so that they can be properly broadcasted to the 
            dimensions of q and k. For example, note
            that cos[position_ids] and sin[position_ids] have the shape 
            [batch_size, seq_len, head_dim]. Then, if q and
            k have the shape [batch_size, heads, seq_len, head_dim], then setting unsqueeze_dim=1 makes
            cos[position_ids] and sin[position_ids] broadcastable to
             the shapes of q and k. Similarly, if q and k have
            the shape [batch_size, seq_len, heads, head_dim], then set unsqueeze_dim=2.
    Returns:
        `tuple(torch.Tensor)` comprising of the query and key tensors rotated using the Rotary Position Embedding.
    """
    cos = cos.unsqueeze(unsqueeze_dim)
    sin = sin.unsqueeze(unsqueeze_dim)
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed


# Copied from transformers.models.llama.modeling_llama.repeat_kv
def repeat_kv(hidden_states: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    This is the equivalent of torch.repeat_interleave(x, dim=1, repeats=n_rep). The hidden states go from (batch,
    num_key_value_heads, seqlen, head_dim) to (batch, num_attention_heads, seqlen, head_dim)
    """
    batch, num_key_value_heads, slen, head_dim = hidden_states.shape
    if n_rep == 1:
        return hidden_states
    hidden_states = hidden_states[:, :, None, :, :].expand(batch, num_key_value_heads, n_rep, slen, head_dim)
    return hidden_states.reshape(batch, num_key_value_heads * n_rep, slen, head_dim)


class SuryaOCRDecoderSdpaCrossAttention(nn.Module):
    """Multi-headed attention from 'Attention Is All You Need' paper
    Modified for GQA
    """

    def __init__(self, config: SuryaOCRDecoderConfig):
        """init"""
        super().__init__()
        self.config = config
        self.attention_dropout = config.attention_dropout
        self.hidden_size = config.hidden_size
        self.num_attention_heads = config.num_attention_heads
        self.head_dim = config.head_dim
        self.num_key_value_heads = config.num_key_value_heads
        self.num_key_value_groups = self.num_attention_heads // self.num_key_value_heads

        self.q_proj = nn.Linear(self.hidden_size, self.num_attention_heads * self.head_dim, bias=config.attention_bias)
        self.k_proj = nn.Linear(self.config.encoder_hidden_size,
                                 self.num_key_value_heads * self.head_dim, bias=config.attention_bias)
        self.v_proj = nn.Linear(self.config.encoder_hidden_size,
                                 self.num_key_value_heads * self.head_dim, bias=config.attention_bias)
        self.o_proj = nn.Linear(self.num_attention_heads * self.head_dim, self.hidden_size, bias=True)
        self.rotary_emb = SuryaOCRDecoderRotaryEmbedding(
            self.head_dim,
            base=config.rope_theta,
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        encoder_hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        encoder_attention_mask: Optional[torch.Tensor] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple[torch.Tensor]]]:
        """forward"""
        # Encoder attention mask currently ignored

        bsz, q_len, _ = hidden_states.size()
        _, v_len, _ = encoder_hidden_states.size()

        query_states = self.q_proj(hidden_states)
        query_states = query_states.view(bsz, q_len, self.num_attention_heads, self.head_dim).transpose(1, 2)

        if self.key_states is None:
            key_states = self.k_proj(encoder_hidden_states)
            value_states = self.v_proj(encoder_hidden_states)
            key_states = key_states.view(bsz, v_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
            value_states = value_states.view(bsz, v_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
            if use_cache:
                self._update_cache(key_states, value_states)
        else:
            key_states = self.key_states
            value_states = self.value_states

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)

        attn_output = torch.nn.functional.scaled_dot_product_attention(
            query_states.contiguous(),
            key_states.contiguous(),
            value_states.contiguous(),
            attn_mask=None,
            dropout_p=self.attention_dropout if self.training else 0.0,
            scale=self.head_dim**-0.5,
        )

        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(bsz, q_len, self.hidden_size)
        attn_output = self.o_proj(attn_output)
        return attn_output

    def _setup_cache(self, batch_size, device, dtype=None):
        """set up caches"""
        # Setup initial caches
        self.value_states = None
        self.key_states = None

    @torch.no_grad()
    def _update_cache(self, key_states, value_states, **cache_kwargs):
        """update caches"""
        self.value_states = value_states
        self.key_states = key_states


class SuryaOCRDecoderSdpaAttention(nn.Module):
    """Multi-headed attention from 'Attention Is All You Need' paper"""

    def __init__(self, config: SuryaOCRDecoderConfig):
        """init"""
        super().__init__()
        self.config = config
        self.attention_dropout = config.attention_dropout
        self.hidden_size = config.hidden_size
        self.num_attention_heads = config.num_attention_heads
        self.head_dim = config.head_dim
        self.num_key_value_heads = config.num_key_value_heads
        self.num_key_value_groups = self.num_attention_heads // self.num_key_value_heads

        self.q_proj = nn.Linear(self.hidden_size, self.num_attention_heads * self.head_dim, bias=config.attention_bias)
        self.k_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=config.attention_bias)
        self.v_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=config.attention_bias)
        self.o_proj = nn.Linear(self.num_attention_heads * self.head_dim, self.hidden_size, bias=True)
        self.rotary_emb = SuryaOCRDecoderRotaryEmbedding(
            self.head_dim,
            base=config.rope_theta,
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        position_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        cache_position: Optional[torch.LongTensor] = None,
        use_cache: bool = False,
        window_attn: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple[torch.Tensor]]]:
        """forward"""
        bsz, q_len, _ = hidden_states.size()

        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        # Final is bsz, num_attention_heads, seq_len, head_dim
        query_states = query_states.view(bsz, q_len, self.num_attention_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary_emb(value_states, position_ids, seq_len=None)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        if use_cache and hasattr(self, "key_states"):
            cache_kwargs = {"cache_position": cache_position, "window_attn": window_attn}
            key_states, value_states = self._update_cache(key_states, value_states, **cache_kwargs)

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)

        causal_mask = attention_mask
        if attention_mask is not None:
            # Mask is batch, head, seq_len, kv_len
            causal_mask = causal_mask[:, :, :, :key_states.shape[-2]]
            current_cache_position = cache_position[-1].item() if cache_position is not None else None
            if current_cache_position and settings.RECOGNITION_STATIC_CACHE:
                # Mask out future cache positions
                position_mask = torch.ones_like(causal_mask, dtype=torch.bool, device=causal_mask.device)
                position_mask[:, :, :, :current_cache_position + 1] = False
                causal_mask = torch.where(position_mask, torch.finfo(causal_mask.dtype).min, causal_mask)

        attn_output = torch.nn.functional.scaled_dot_product_attention(
            query_states.contiguous(),
            key_states.contiguous(),
            value_states.contiguous(),
            attn_mask=causal_mask,
            dropout_p=self.attention_dropout if self.training else 0.0,
            scale=self.head_dim**-0.5,
        )

        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(bsz, q_len, self.hidden_size)
        attn_output = self.o_proj(attn_output)
        return attn_output

    def _setup_cache(self, batch_size, device, dtype=None):
        """set up caches"""
        if dtype is None and self.config.torch_dtype is not None:
            dtype = self.config.torch_dtype
        dtype = dtype if dtype is not None else torch.float32

        # Setup initial caches
        self.value_states = None
        self.key_states = None

        if settings.RECOGNITION_STATIC_CACHE:
            cache_shape = (batch_size, self.num_key_value_heads, settings.RECOGNITION_MAX_TOKENS, self.head_dim)
            self.value_states = torch.zeros(cache_shape, dtype=dtype, device=device)
            self.key_states = torch.zeros(cache_shape, dtype=dtype, device=device)

    def _update_static_cache(self, key_states, value_states, **cache_kwargs):
        """update caches"""
        cache_position = cache_kwargs.get("cache_position")
        k_out, v_out = self.key_states.to(key_states.device), self.value_states.to(value_states.device)

        k_out[:, :, cache_position] = key_states.to(k_out.dtype)
        v_out[:, :, cache_position] = value_states.to(v_out.dtype)

        self.key_states, self.value_states = k_out, v_out
        return k_out, v_out

    def _update_dynamic_cache(self, key_states, value_states, **cache_kwargs):
        """"update caches"""
        k_out = key_states
        if self.key_states is not None:
            k_out = torch.cat([self.key_states, key_states], dim=2)

        v_out = value_states
        if self.value_states is not None:
            v_out = torch.cat([self.value_states, value_states], dim=2)

        self.key_states, self.value_states = k_out, v_out
        return k_out, v_out

    @torch.no_grad()
    def _update_cache(self, key_states, value_states, **cache_kwargs):
        """update caches"""
        if settings.RECOGNITION_STATIC_CACHE:
            return self._update_static_cache(key_states, value_states, **cache_kwargs)

        return self._update_dynamic_cache(key_states, value_states, **cache_kwargs)


class SuryaOCRDecoderMlp(nn.Module):
    """MLP module from 'Attention Is All You Need' paper"""
    def __init__(self, config):
        """init"""
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.gate_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.up_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.down_proj = nn.Linear(self.intermediate_size, self.hidden_size, bias=False)
        if config.hidden_activation is None:
            config.hidden_activation = "gelu_pytorch_tanh"
        hidden_activation = config.hidden_activation
        self.act_fn = ACT2FN[hidden_activation]

    def forward(self, x):
        """forward"""
        return self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x))


class SuryaOCRDecoderLayer(nn.Module):
    """Decoder layer from 'Attention Is All You Need' paper"""
    def __init__(self, config, layer_idx):
        """init"""
        super().__init__()
        super().__init__()
        self.cross_pre_norm = SuryaOCRDecoderRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.temporal_pre_norm = SuryaOCRDecoderRMSNorm(config.hidden_size, eps=config.rms_norm_eps)

        self.temporal_block = None
        if layer_idx in config.self_attn_layers:
            self.temporal_block = SuryaOCRDecoderSdpaAttention(config)

        self.cross_attn_block = None
        if layer_idx in config.cross_attn_layers:
            self.cross_attn_block = SuryaOCRDecoderSdpaCrossAttention(config)

        self.window_attn = layer_idx not in config.global_attn_layers
        self.channel_pre_norm = SuryaOCRDecoderRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.mlp_block = SuryaOCRDecoderMlp(config)

    def forward(
        self,
        activations: torch.Tensor,
        position_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        encoder_hidden_states: torch.Tensor = None,
        encoder_attention_mask: torch.Tensor = None,
        cache_position: torch.Tensor = None,
        use_cache: bool = None,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """forward"""
        raw_activations = activations

        if self.cross_attn_block is not None:
            # Do cross-attention on encoder outputs
            cross_attn_inputs = self.cross_pre_norm(activations)
            cross_attn_path = self.cross_attn_block(
                cross_attn_inputs, encoder_hidden_states, attention_mask, encoder_attention_mask, use_cache=use_cache
            )
            cross_attn_output = cross_attn_path + raw_activations
        else:
            cross_attn_output = raw_activations

        if self.temporal_block is not None:
            # RMSNorm introduces slight slight differences
            inputs_normalized = self.temporal_pre_norm(cross_attn_output) 
            hidden_states = self.temporal_block(
                inputs_normalized, position_ids, attention_mask, 
                cache_position=cache_position, use_cache=use_cache, window_attn=self.window_attn
            )

            residual = hidden_states + raw_activations
        else:
            residual = cross_attn_output

        hidden_states = self.channel_pre_norm(residual)
        hidden_states = self.mlp_block(hidden_states)

        hidden_states = hidden_states + residual
        return hidden_states


class SuryaOCRDecoderPreTrainedModel(PreTrainedModel):
    """Transformer Decoder model"""
    config_class = SuryaOCRDecoderConfig
    base_model_prefix = "model"
    supports_gradient_checkpointing = True
    _no_split_modules = ["SuryaOCRDecoderLayer"]
    _skip_keys_device_placement = ["cache"]
    _supports_flash_attn_2 = False
    _supports_sdpa = False  # we can't compare with eager for now
    _supports_cache_class = True
    _supports_quantized_cache = True

    def _init_weights(self, module):
        """init weights"""
        if isinstance(module, SuryaOCRDecoderSdpaAttention):
            torch.nn.init.normal_(module.q_proj.weight, mean=0.0, std=self.config.init_std)
            torch.nn.init.normal_(module.k_proj.weight, mean=0.0, std=self.config.init_std)
            torch.nn.init.normal_(module.v_proj.weight, mean=0.0, std=self.config.init_std)

            torch.nn.init.normal_(module.o_proj.weight, mean=0.0, std=self.config.init_std)
        elif isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
            if getattr(module, "bias", None) is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.init_std)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()

    def _setup_cache(self, config, batch, device, dtype):
        """setup cache"""
        layers = getattr(self, "model", self).layers
        for layer in layers:
            if layer.temporal_block:
                layer.temporal_block._setup_cache(batch, device, dtype)
            if layer.cross_attn_block:
                layer.cross_attn_block._setup_cache(batch, device, dtype)

    def reset_cache(self, batch, device, dtype):
        """reset cache"""
        pass

    def _tie_weights(self):
        """tie weights"""
        pass

    def tie_weights(self):
        """tie weights"""
        pass


class SuryaOCRDecoderModel(SuryaOCRDecoderPreTrainedModel):
    """
    Transformer decoder consisting of *config.num_hidden_layers* layers. Each layer is a [`SuryaOCRDecoderDecoderLayer`]

    Args:
        config: SuryaOCRDecoderConfig
    """

    def __init__(self, config: SuryaOCRDecoderConfig):
        """init"""
        super().__init__(config)
        self.padding_idx = config.pad_token_id
        self.vocab_size = config.vocab_size
        self.causal = config.causal

        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size, self.padding_idx)
        self.layers = nn.ModuleList(
            [SuryaOCRDecoderLayer(config, layer_idx) for layer_idx in range(config.num_hidden_layers)]
        )
        self.final_norm = SuryaOCRDecoderRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.gradient_checkpointing = False

        self.register_buffer(
            "normalizer", torch.tensor(self.config.hidden_size**0.5, dtype=torch.float32), persistent=False
        )
        # Initialize weights and apply final processing
        self.post_init()

    # Copied from transformers.models.llama.modeling_llama.LlamaModel.get_input_embeddings
    def get_input_embeddings(self):
        """get input embeddings"""
        return self.embed_tokens

    # Copied from transformers.models.llama.modeling_llama.LlamaModel.set_input_embeddings
    def set_input_embeddings(self, value):
        """set input embeddings"""
        self.embed_tokens = value

    def forward(
        self,
        input_ids: torch.LongTensor = None,
        position_ids: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        encoder_hidden_states: Optional[torch.FloatTensor] = None,
        encoder_attention_mask: Optional[torch.FloatTensor] = None,
        cache_position: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        prefill: bool = False
    ) -> Union[Tuple, BaseModelOutputWithNoAttention]:
        """forward"""
        use_cache = use_cache if use_cache is not None else self.config.use_cache
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if self.gradient_checkpointing and self.training and use_cache:
            use_cache = False

        inputs_embeds = self.embed_tokens(input_ids)
        hidden_states = inputs_embeds

        if use_cache and prefill:
            self._setup_cache(self.config, hidden_states.shape[0], hidden_states.device, hidden_states.dtype)

        if cache_position is None:
            cache_position = torch.arange(hidden_states.shape[1], device=hidden_states.device)
        if position_ids is None:
            position_ids = cache_position.unsqueeze(0)

        causal_mask = self._update_causal_mask(attention_mask, inputs_embeds, cache_position)

        all_hidden_states = () if output_hidden_states else None
        for i, residual_block in enumerate(self.layers):
            if output_hidden_states:
                all_hidden_states += (hidden_states,)
            if self.gradient_checkpointing and self.training:
                hidden_states = self._gradient_checkpointing_func(
                    residual_block.__call__, hidden_states, position_ids, causal_mask, 
                                             encoder_hidden_states, encoder_attention_mask, cache_position, use_cache
                )
            else:
                hidden_states = residual_block(hidden_states, position_ids, causal_mask,   
                                             encoder_hidden_states, encoder_attention_mask, cache_position, use_cache)

        hidden_states = self.final_norm(hidden_states)

        # add hidden states from the last decoder layer
        if output_hidden_states:
            all_hidden_states += (hidden_states,)

        if not return_dict:
            return tuple(v for v in [hidden_states, all_hidden_states] if v is not None)

        return BaseModelOutputWithNoAttention(
            last_hidden_state=hidden_states,
            hidden_states=all_hidden_states,
        )

    # TODO: As of torch==2.2.0, the `attention_mask` passed to the model in 
    # `generate` is 2D and of dynamic length even when the static
    # KV cache is used. This is an issue for torch.compile which then 
    # recaptures cudagraphs at each decode steps due to the dynamic shapes.
    # (`recording cudagraph tree for symint key 13`, etc.), which is VERY slow.
    # A workaround is `@torch.compiler.disable`, but this prevents using
    # `fullgraph=True`. See more context in https://github.com/huggingface/transformers/pull/29114
    # Ignore copy
    def _update_causal_mask(self, attention_mask, input_tensor, cache_position):
        """update causal mask"""
        if not self.causal:
            return None

        dtype, device = input_tensor.dtype, input_tensor.device
        min_dtype = torch.finfo(dtype).min
        sequence_length = input_tensor.shape[1]
        target_length = max(settings.RECOGNITION_MAX_TOKENS, sequence_length)

        diagonal = torch.full((sequence_length, target_length), fill_value=min_dtype, dtype=dtype, device=device)
        causal_mask = diagonal
        if sequence_length != 1:
            # Select the upper triangular part of the matrix, but unmask current token (the diagonal)
            # triu will be the min_dtype, everything else is 0 (attended to)
            causal_mask = torch.triu(diagonal, diagonal=1)

        causal_mask *= torch.arange(target_length, device=device) > cache_position.reshape(-1, 1)
        causal_mask = causal_mask[None, None, :, :].expand(input_tensor.shape[0], 1, -1, -1)
        if attention_mask is not None:
            causal_mask = causal_mask.clone()  # copy to contiguous memory for in-place edit
            if attention_mask.dim() == 2:
                # Mask positions in the causal mask that are masked in the attention mask
                mask_length = attention_mask.shape[-1]
                padding_mask = causal_mask[..., :mask_length].eq(0.0) * attention_mask[:, None, None, :].eq(0.0)
                causal_mask[..., :mask_length] = causal_mask[..., :mask_length].masked_fill(padding_mask, min_dtype)

        if attention_mask is not None and attention_mask.device.type == "cuda":
            # Attend to all tokens in fully masked rows in the causal_mask, for example the relevant first rows when
            # using left padding. This is required by F.scaled_dot_product_attention memory-efficient attention path.
            # Details: https://github.com/pytorch/pytorch/issues/110213
            causal_mask = AttentionMaskConverter._unmask_unattended(causal_mask, min_dtype)

        return causal_mask


class SuryaOCRDecoder(SuryaOCRDecoderPreTrainedModel):
    """surya ocr decoder"""
    _tied_weights_keys = None

    def __init__(self, config, **kwargs):
        """init"""
        super().__init__(config)
        self.model = SuryaOCRDecoderModel(config)
        self.vocab_size = config.vocab_size
        aux_heads = config.aux_heads if config.aux_heads is not None else 0
        lm_heads = aux_heads + 1
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size * lm_heads, bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        """get input embeddings"""
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        """set input embeddings"""
        self.model.embed_tokens = value

    def get_output_embeddings(self):
        """get output embeddings"""
        return self.lm_head

    def set_output_embeddings(self, new_embeddings):
        """set output embeddings"""
        self.lm_head = new_embeddings

    def set_decoder(self, decoder):
        """set decoder"""
        self.model = decoder

    def get_decoder(self):
        """get decoder"""
        return self.model

    # Ignore copy
    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        cache_position: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        encoder_hidden_states: Optional[torch.FloatTensor] = None,
        encoder_attention_mask: Optional[torch.FloatTensor] = None,
        use_cache: Optional[bool] = None,
        prefill: bool = False,
        **kwargs
    ) -> Union[Tuple, OCRModelOutput]:
        """forward"""
        outputs = self.model(
            input_ids=input_ids,
            cache_position=cache_position,
            attention_mask=attention_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=use_cache,
            output_hidden_states=True,
            return_dict=True,
            prefill=prefill,
        )

        hidden_states = outputs[0]
        all_logits = self.lm_head(hidden_states)
        all_logits = torch.split(all_logits, self.vocab_size, dim=-1)
        logits = all_logits[0]
        aux_logits = all_logits[1:] if len(all_logits) > 1 else None

        return OCRModelOutput(
            logits=logits,
            aux_logits=aux_logits,
            hidden_states=outputs.hidden_states,
        )


@dataclass
class TextEncoderOutput(CausalLMOutput):
    """ TextEncoderOutput """
    hidden_states: torch.FloatTensor = None


class SuryaOCRTextEncoder(SuryaOCRDecoderPreTrainedModel):
    """ SuryaOCRTextEncoder """
    _tied_weights_keys = None
    config_class = SuryaOCRTextEncoderConfig

    def __init__(self, config, **kwargs):
        """ init """
        super().__init__(config)
        self.model = SuryaOCRDecoderModel(config)
        self.vocab_size = config.vocab_size

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        """ get input embeddings """
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        """ set input embeddings """
        self.model.embed_tokens = value

    def set_decoder(self, decoder):
        """ set decoder """
        self.model = decoder

    def get_decoder(self):
        """ get decoder """
        return self.model

    # Ignore copy
    def forward(
        self,
        input_ids: Optional[torch.LongTensor] = None,
        cache_position: Optional[torch.LongTensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        encoder_hidden_states: Optional[torch.FloatTensor] = None,
        encoder_attention_mask: Optional[torch.FloatTensor] = None,
        use_cache: Optional[bool] = None,
        **kwargs
    ) -> Union[Tuple, CausalLMOutput]:
        """ forward """
        outputs = self.model(
            input_ids=input_ids,
            cache_position=cache_position,
            attention_mask=attention_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=use_cache,
            output_hidden_states=True,
            return_dict=True,
        )

        return TextEncoderOutput(
            hidden_states=outputs.last_hidden_state,
        )