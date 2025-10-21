#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
Setup script.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""


from transformers import DetrConfig, BeitConfig, DetrImageProcessor, VisionEncoderDecoderConfig, AutoModelForCausalLM, \
    AutoModel
from src.rock.model.ordering.config import MBartOrderConfig, VariableDonutSwinConfig
from src.rock.model.ordering.decoder import MBartOrder
from src.rock.model.ordering.encoder import VariableDonutSwinModel
from src.rock.model.ordering.encoderdecoder import OrderVisionEncoderDecoderModel
from src.rock.model.ordering.processor import OrderImageProcessor
from src.rock.settings import settings


def load_model(checkpoint=settings.ORDER_MODEL_CHECKPOINT, 
                    device=settings.TORCH_DEVICE_MODEL, dtype=settings.MODEL_DTYPE):
    """load model"""
    config = VisionEncoderDecoderConfig.from_pretrained(checkpoint)

    decoder_config = vars(config.decoder)
    decoder = MBartOrderConfig(**decoder_config)
    config.decoder = decoder

    encoder_config = vars(config.encoder)
    encoder = VariableDonutSwinConfig(**encoder_config)
    config.encoder = encoder

    # Get transformers to load custom model
    AutoModel.register(MBartOrderConfig, MBartOrder)
    AutoModelForCausalLM.register(MBartOrderConfig, MBartOrder)
    AutoModel.register(VariableDonutSwinConfig, VariableDonutSwinModel)

    model = OrderVisionEncoderDecoderModel.from_pretrained(checkpoint, config=config, torch_dtype=dtype)
    assert isinstance(model.decoder, MBartOrder)
    assert isinstance(model.encoder, VariableDonutSwinModel)

    model = model.to(device)
    model = model.eval()
    print(f"Loading reading order model {checkpoint} on device {device} with dtype {dtype}")
    return model