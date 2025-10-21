#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
dab detr model initialization.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import torch.nn as nn

from detrex.modeling import HungarianMatcher, SetCriterion
from detrex.layers import PositionEmbeddingSine
from detrex.modeling.backbone import ResNet, BasicStem
from detectron2.modeling.backbone import SwinTransformer
from detectron2.config import LazyCall as L
import src.config_util as cfg

from src.rock.model.layout.modeling import (
    DABDETR,
    DabDetrTransformer,
    DabDetrTransformerDecoder,
    DabDetrTransformerEncoder,
)


model = L(DABDETR)(
        backbone=L(SwinTransformer)(
            embed_dim=96,
            depths=(2, 2, 6, 2),
            num_heads=(3, 6, 12, 24),
            drop_path_rate=0.1,
            out_indices=(3,),
    ),
    in_features=["p3"],  # only use last level feature in DAB-DETR
    in_channels=768,
    position_embedding=L(PositionEmbeddingSine)(
        num_pos_feats=128,
        temperature=20,
        normalize=True,
    ),
    transformer=L(DabDetrTransformer)(
        encoder=L(DabDetrTransformerEncoder)(
            embed_dim=256,
            num_heads=8,
            attn_dropout=0.0,
            feedforward_dim=2048,
            ffn_dropout=0.0,
            activation=L(nn.PReLU)(),
            num_layers=6,
        ),
        decoder=L(DabDetrTransformerDecoder)(
            embed_dim=256,
            num_heads=8,
            attn_dropout=0.0,
            feedforward_dim=2048,
            ffn_dropout=0.0,
            activation=L(nn.PReLU)(),
            num_layers=6,
            modulate_hw_attn=True,
        ),
        num_patterns=0,  # pattern embedding as in Anchor-DETR
    ),
    embed_dim=256,
    num_classes=11,
    num_queries=300,
    criterion=L(SetCriterion)(
        num_classes=80,
        matcher=L(HungarianMatcher)(
            cost_class=2.0,
            cost_bbox=5.0,
            cost_giou=2.0,
            cost_class_type="focal_loss_cost",
            alpha=0.25,
            gamma=2.0,
        ),
        weight_dict={
            "loss_class": 1,
            "loss_bbox": 5.0,
            "loss_giou": 2.0,
        },
        loss_class_type="focal_loss",
        alpha=0.25,
        gamma=2.0,
    ),
    aux_loss=True,
    pixel_mean=[123.675, 116.280, 103.530],
    pixel_std=[58.395, 57.120, 57.375],
    freeze_anchor_box_centers=True,
    select_box_nums_for_evaluation=300,
    device=cfg.DEVICE,
)

# set aux loss weight dict
if model.aux_loss:
    weight_dict = model.criterion.weight_dict
    aux_weight_dict = {}
    for i in range(model.transformer.decoder.num_layers - 1):
        aux_weight_dict.update({k + f"_{i}": v for k, v in weight_dict.items()})
    weight_dict.update(aux_weight_dict)
    model.criterion.weight_dict = weight_dict
