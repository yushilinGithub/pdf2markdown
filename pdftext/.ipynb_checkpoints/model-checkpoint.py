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

import joblib
import src.config_util as cfg


def get_model(model_path: str=None):
    """
    load model
    """
    if model_path is None:
        model_path = cfg.PDF_EXTRACTION_MODEL
    model = joblib.load(model_path)
    return model

