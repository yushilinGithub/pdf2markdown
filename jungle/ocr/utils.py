#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

def alphanum_ratio(text):
    """
    计算给定文本中字母数字字符所占的比例。
    
    Args:
        text (str): 待计算的文本字符串。
    
    Returns:
        float: 字母数字字符在文本中的比例，即字母数字字符数量除以文本总长度。
    
    """
    text = text.replace(" ", "")
    text = text.replace("\n", "")
    alphanumeric_count = sum([1 for c in text if c.isalnum()])

    if len(text) == 0:
        return 1

    ratio = alphanumeric_count / len(text)
    return ratio
