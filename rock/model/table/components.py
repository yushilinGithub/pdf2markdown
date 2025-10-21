# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
model components

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


import torch
from torch import Tensor, nn
from functools import partial
from typing import Optional, Tuple
import torch
from torch import nn, Tensor
from torchvision.ops.misc import Conv2dNormActivation


class ImgCnnBackbone(nn.Module):
    """Image cnn back bone"""
    def __init__(
        self,
        backbone: nn.Module,
        output_channels: int,
        d_model: int,
        drop_layer: Tuple = None,
    ) -> None:
        super().__init__()

        # drop layers for classification & maxpooling for higher feature resolution
        layers = list(backbone.children())
        nlayer = len(layers)
        keep_layer = set([i for i in range(nlayer)]) - set(drop_layer)
        backbone = [layers[i] for i in keep_layer]
        self.backbone = nn.Sequential(*backbone)
        self.proj = nn.Linear(output_channels, d_model)
        self.channels = output_channels


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        x = self.backbone(x)
        x = x.flatten(start_dim=-2).transpose(1, 2)
        assert x.shape[-1] == self.channels, "Image channels size mismatch."
        x = self.proj(x)
        return x


class ImgLinearBackbone(nn.Module):
    """image linear back bone"""
    def __init__(
        self,
        d_model: int,
        patch_size: int,
        in_chan: int = 3,
    ) -> None:
        """init"""
        super().__init__()

        self.conv_proj = nn.Conv2d(
            in_chan, out_channels=d_model, kernel_size=patch_size, stride=patch_size
        )
        self.d_model = d_model


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        x = self.conv_proj(x)
        x = x.flatten(start_dim=-2).transpose(1, 2)
        return x


class ImgConvStemBackbone(nn.Module):
    """back bone"""
    def __init__(
        self,
        d_model: int,
        downsample_factor: int,
        output_channels: int,
        kernel_size: int,
    ) -> None:
        """init"""
        super().__init__()

        assert downsample_factor % 2 == 0
        assert output_channels % (downsample_factor // 2) == 0
        input_channels = output_channels // (downsample_factor // 2)

        layers = [
            Conv2dNormActivation(
                3, input_channels, kernel_size=kernel_size, stride=2, padding=1
            )
        ]

        while input_channels != output_channels:
            layers.append(
                Conv2dNormActivation(
                    input_channels,
                    input_channels * 2,
                    kernel_size=kernel_size,
                    stride=2,
                    padding=1,
                )
            )
            input_channels = input_channels * 2

        layers.append(nn.Conv2d(output_channels, d_model, kernel_size=1))

        self.conv_stem = nn.Sequential(*layers)


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        x = self.conv_stem(x)
        x = x.flatten(start_dim=-2).transpose(1, 2)
        return x


class Encoder(nn.Module):
    """encoder"""
    def __init__(
        self,
        d_model: int,
        nhead: int,
        dropout: float,
        activation: str,
        norm_first: bool,
        nlayer: int,
        ff_ratio: int = 4,
    ) -> None:
        """init"""
        super().__init__()

        encoder_layer = nn.TransformerEncoderLayer(
            d_model,
            nhead=nhead,
            dim_feedforward=ff_ratio * d_model,
            dropout=dropout,
            activation=activation,
            batch_first=True,
            norm_first=norm_first,
        )

        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=nlayer)


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        x = self.encoder(x)
        return x


class Decoder(nn.Module):
    """deocder"""
    def __init__(
        self,
        d_model: int,
        nhead: int,
        dropout: float,
        activation: str,
        norm_first: bool,
        nlayer: int,
        ff_ratio: int = 4,
    ) -> None:
        """init"""
        super().__init__()
        decoder_layer = nn.TransformerDecoderLayer(
            d_model,
            nhead,
            dim_feedforward=ff_ratio * d_model,
            dropout=dropout,
            activation=activation,
            batch_first=True,
            norm_first=norm_first,
        )

        self.decoder = nn.TransformerDecoder(decoder_layer, nlayer)


    def forward(
        self, x: Tensor, memory: Tensor, tgt_mask: Tensor, tgt_padding_mask: Tensor
    ) -> Tensor:
        """forward"""
        x = self.decoder(
            x, memory, tgt_mask=tgt_mask, tgt_key_padding_mask=tgt_padding_mask
        )
        return x


class PositionEmbedding(nn.Module):
    """embedding"""
    def __init__(self, max_seq_len: int, d_model: int, dropout: float) -> None:
        """init"""
        super().__init__()
        self.embedding = nn.Embedding(max_seq_len, d_model)
        self.dropout = nn.Dropout(dropout)


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        # assume x is batch first
        out = self.embedding(torch.arange(x.shape[1], device=x.device))
        return self.dropout(out + x)


class TokenEmbedding(nn.Module):
    """embedding"""
    def __init__(
        self,
        vocab_size: int,
        d_model: int,
        padding_idx: int,
    ) -> None:
        """init"""
        super().__init__()
        assert vocab_size > 0
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)


    def forward(self, x: Tensor) -> Tensor:
        """forward"""
        return self.embedding(x)


class PrintLayer(nn.Module):
    """Only for debugging when loss is nan."""


    def __init__(self):
        """init"""
        super().__init__()


    def forward(self, x):
        """forward"""
        print(
            "torch.isfinite(x).all(): {}, min. {:.5f}, max. {:.5f}".format(
                torch.isfinite(x).all(), x.min(), x.max()
            )
        )
        return x


class EncoderDecoder(nn.Module):
    """Encoder decoder architecture that takes in a tabular image and generates the text output.
    Backbone serves as the image processor. There are three types of backbones: CNN, linear projection, and ConvStem.

    Args:
    ----
        backbone: tabular image processor
        encoder: transformer encoder
        decoder: transformer decoder
        vocab_size: size of the vocabulary
        d_model: feature size
        padding_idx: index of <pad> in the vocabulary
        max_seq_len: max sequence length of generated text
        dropout: dropout rate
        norm_layer: layernorm
        init_std: std in weights initialization
    """

    def __init__(
        self,
        backbone: nn.Module,
        encoder: nn.Module,
        decoder: nn.Module,
        vocab_size: int,
        d_model: int,
        padding_idx: int,
        max_seq_len: int,
        dropout: float,
        norm_layer: nn.Module,
        init_std: float = 0.02,
    ):
        """init"""
        super().__init__()

        self.backbone = backbone
        self.encoder = encoder
        self.decoder = decoder
        self.norm = norm_layer(d_model)
        self.token_embed = TokenEmbedding(
            vocab_size=vocab_size, d_model=d_model, padding_idx=padding_idx
        )
        self.pos_embed = PositionEmbedding(
            max_seq_len=max_seq_len, d_model=d_model, dropout=dropout
        )
        self.generator = nn.Linear(d_model, vocab_size)

        self.trunc_normal = partial(
            nn.init.trunc_normal_, std=init_std, a=-init_std, b=init_std
        )
        self.apply(self._init_weights)


    def _init_weights(self, m: nn.Module):
        """ init weight"""
        if isinstance(m, nn.Linear):
            self.trunc_normal(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.weight, 1.0)
            nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, nn.Conv2d):
            self.trunc_normal(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, PositionEmbedding):
            self.trunc_normal(m.embedding.weight)
        elif isinstance(m, TokenEmbedding):
            self.trunc_normal(m.embedding.weight)


    @torch.jit.ignore
    def no_weight_decay(self):
        """no_weight_decay"""
        return {"token_embed", "pos_embed"}


    def encode(self, src: Tensor) -> Tensor:
        """encode"""
        src_feature = self.backbone(src)
        src_feature = self.pos_embed(src_feature)
        memory = self.encoder(src_feature)
        memory = self.norm(memory)
        return memory


    def decode(
        self, memory: Tensor, tgt: Tensor, tgt_mask: Tensor, tgt_padding_mask: Tensor
    ) -> Tensor:
        """decode"""
        tgt_feature = self.pos_embed(self.token_embed(tgt))
        tgt = self.decoder(tgt_feature, memory, tgt_mask, tgt_padding_mask)

        return tgt

    def forward(
        self, src: Tensor, tgt: Tensor, tgt_mask: Tensor, tgt_padding_mask: Tensor
    ) -> Tensor:
        """f"""
        memory = self.encode(src)
        tgt = self.decode(memory, tgt, tgt_mask, tgt_padding_mask)
        tgt = self.generator(tgt)

        return tgt


class BeitEncoder(nn.Module):
    """BeitEncoder"""
    def __init__(
        self,
        d_model: int,  # embed_dim
        backbone: nn.Module,
        max_seq_len: int,  # for positional embedding
        codebook_tokens: int,
        dropout: float,
        encoder: Encoder,
        norm_layer: nn.Module,
        init_std: float = 0.02,
    ) -> None:
        """init"""
        super().__init__()

        self.d_model = d_model
        self.init_std = init_std

        self.backbone = backbone
        self.pos_embed = PositionEmbedding(
            max_seq_len=max_seq_len, d_model=d_model, dropout=dropout
        )

        self.encoder = encoder
        self.norm = norm_layer(d_model)
        self.generator = nn.Linear(d_model, codebook_tokens)

        self.trunc_normal = partial(
            nn.init.trunc_normal_, std=init_std, a=-init_std, b=init_std
        )
        self.apply(self._init_weights)

        self.mask_token = nn.Parameter(torch.zeros(1, 1, d_model))


    def _init_weights(self, m: nn.Module):
        """_init_weight"""
        if isinstance(m, nn.Linear):
            self.trunc_normal(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.weight, 1.0)
            nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, nn.Conv2d):
            self.trunc_normal(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0.0)
        elif isinstance(m, PositionEmbedding):
            self.trunc_normal(m.embedding.weight)


    @torch.jit.ignore
    def no_weight_decay(self):
        """no_weight_decay"""
        return {"pos_embed"}


    def forward(
        self, x: Tensor, bool_masked_pos: Tensor, return_all_tokens: bool = False
    ):
        """forward"""
        x = self.backbone(x)
        B, S, E = x.shape
        assert E == self.d_model

        mask_token = self.mask_token.expand(B, S, -1)

        w = bool_masked_pos.unsqueeze(-1).type_as(mask_token)
        x = x * (1 - w) + mask_token * w

        x = self.pos_embed(x)

        x = self.encoder(x)
        x = self.norm(x)

        if return_all_tokens:
            return self.generator(x)
        else:
            return self.generator(x[bool_masked_pos])