#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(yushilin@baidu.com)
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
