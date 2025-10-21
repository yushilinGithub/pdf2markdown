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

from transformers import MBartConfig, DonutSwinConfig


class MBartOrderConfig(MBartConfig):
    """M"""
    pass


class VariableDonutSwinConfig(DonutSwinConfig):
    """V"""
    pass