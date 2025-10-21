#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
Setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from transformers import MBartConfig, DonutSwinConfig


class MBartOrderConfig(MBartConfig):
    """M"""
    pass


class VariableDonutSwinConfig(DonutSwinConfig):
    """V"""
    pass