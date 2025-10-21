#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author: 1329239119@qq.com
title level recognition
"""

import re


def get_all_character(text: str):
    """
    获取文本中所有字符，包含中文字符，英文字符
    """
    return "".join(re.findall(r'[\u4e00-\u9fa5a-zA-Z]', text))


def contain_chinese(text: str) -> bool:
    """
    判断字符串是否包含中文。
    
    Args:
        text (str): 待判断的字符串。
    
    Returns:
        bool: 是否包含中文。
    """
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False



def count_ch_characters(text):
    """
    计算文本中中文字符的数量。
    
    Args:
        text (str): 待计算的文本字符串。
    
    Returns:
        int: 文本中中文字符的数量。
    
    """
    chinese_count = len(re.findall(r'[\u4e00-\u9fa5]', text))
    return chinese_count