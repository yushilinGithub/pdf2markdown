#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
merged_block.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""

from collections import Counter
from typing import List, Optional

from pydantic import BaseModel

from src.jungle.schema.bbox import BboxElement
from src.jungle.schema.block import Span

class MergedLine(BboxElement):
    """
    Merged line in a merged block.
    """
    text: str
    fonts: List[str]
    table_cell_bbox: Optional[list] = None

    def most_common_font(self):
        """most common font"""
        counter = Counter(self.fonts)
        return counter.most_common(1)[0][0]


class MergedBlock(BboxElement):
    """
    Merged block 
    """
    lines: List[MergedLine]
    pnum: int
    block_type: Optional[str]
    spans: List[Span]
    html_code: Optional[str] = None
    table_trust: Optional[bool] = True


class FullyMergedBlock(BaseModel):
    """
    FullyMergedBlock
    """
    text: str
    block_type: str
