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


def sort_table_blocks(blocks, tolerance=5):
    """
    Sort table blocks by their top Y coordinate within a given tolerance range.
    """
    vertical_groups = {}
    for block in blocks:
        if hasattr(block, "bbox"):
            bbox = block.bbox
        else:
            bbox = block["bbox"]
        group_key = round(bbox[1] / tolerance)
        if group_key not in vertical_groups:
            vertical_groups[group_key] = []
        vertical_groups[group_key].append(block)

    # Sort each group horizontally and flatten the groups into a single list
    sorted_blocks = []
    for _, group in sorted(vertical_groups.items()):
        sorted_group = sorted(group, key=lambda x: x.bbox[0] if hasattr(x, "bbox") else x["bbox"][0])
        sorted_blocks.extend(sorted_group)

    return sorted_blocks


def replace_dots(text):
    """
    Replace dots with spaces to avoid splitting words across lines.
    """
    dot_pattern = re.compile(r'(\s*\.\s*){4,}')
    dot_multiline_pattern = re.compile(r'.*(\s*\.\s*){4,}.*', re.DOTALL)

    if dot_multiline_pattern.match(text):
        text = dot_pattern.sub(' ', text)
    return text


def replace_newlines(text):
    """
     Replace all newlines
    """
    newline_pattern = re.compile(r'[\r\n]+')
    return newline_pattern.sub(' ', text.strip())
