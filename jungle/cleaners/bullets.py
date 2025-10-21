#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import re


def replace_bullets(text):
    """
    # Replace bullet characters with a -
    """
    bullet_pattern = r"(^|[\n ])[•●○■▪▫–—]( )"
    replaced_string = re.sub(bullet_pattern, r"\1-\2", text)
    return replaced_string
