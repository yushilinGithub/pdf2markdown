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

import math
from typing import List, Optional, Dict, Union

from pydantic import field_validator
import ftfy

from src.jungle.schema.bbox import BboxElement
from src.jungle.settings import settings


class BlockType(BboxElement):
    """Blocktype"""
    block_type: str


class Span(BboxElement):
    """span"""
    chars: Union[List[Dict], None] = None # none if using ocr 
    text: str
    span_id: str
    rotation: float
    font: str
    font_weight: float
    font_size: float
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    image: Optional[bool] = None


    @field_validator('text')
    @classmethod
    def fix_unicode(cls, text: str) -> str:
        return ftfy.fix_text(text)


class Line(BboxElement):
    """line"""
    spans: List[Span]

    @property
    def prelim_text(self):
        """prelim text"""
        return "".join([s.text for s in self.spans])

    @property
    def start(self):
        """start"""
        return self.spans[0].bbox[0]


class Block(BboxElement):
    """block"""
    lines: List[Line]
    pnum: int
    block_type: Optional[str] = None
    position: Optional[int] = None
    html_code: Optional[str] = None
    table_trust: Optional[bool] = True

    @property
    def prelim_text(self):
        """prelim _text"""
        return "\n".join([l.prelim_text for l in self.lines])

    @property
    def block_font_sizes(self):
        """block font sizes"""
        block_font_sizes = []
        for line in self.lines:
            line_font_sizes = []
            for span in line.spans:
                line_font_sizes.append(span.font_size)
            block_font_sizes.append(line_font_sizes)
        return block_font_sizes
    
    @property
    def block_font_weights(self):
        """block font sizes"""
        block_font_weights = []
        for line in self.lines:
            line_font_weights = []
            for span in line.spans:
                line_font_weights.append(span.font_weight)
            block_font_weights.append(line_font_weights)
        return block_font_weights

    @property
    def block_fonts(self):
        """block fonts"""
        block_fonts = []
        for line in self.lines:
            line_fonts = []
            for span in line.spans:
                line_fonts.append(span.font)
            block_fonts.append(line_fonts)
        return block_fonts

    def filter_spans(self, bad_span_ids):
        """filter spans"""

        new_lines = []
        for line in self.lines:
            new_spans = []
            for span in line.spans:
                if not span.span_id in bad_span_ids:
                    new_spans.append(span)
            line.spans = new_spans
            if len(new_spans) > 0:
                new_lines.append(line)
        self.lines = new_lines

    def filter_bad_span_types(self):
        """filter bad span"""
        new_lines = []
        for line in self.lines:
            new_spans = []
            for span in line.spans:
                if self.block_type not in settings.BAD_SPAN_TYPES:
                    new_spans.append(span)
            line.spans = new_spans
            if len(new_spans) > 0:
                new_lines.append(line)
        self.lines = new_lines

    def get_min_line_start(self):
        """get min line start"""
        line_starts = [line.start for line in self.lines]
        if len(line_starts) == 0:
            return None
        return min(line_starts)


def bbox_from_lines(lines: List[Line]):
    """bbox from lines"""
    min_x = min([line.bbox[0] for line in lines])
    min_y = min([line.bbox[1] for line in lines])
    max_x = max([line.bbox[2] for line in lines])
    max_y = max([line.bbox[3] for line in lines])
    return [min_x, min_y, max_x, max_y]


def split_block_lines(block: Block, split_line_idx: int):
    """split block lines"""
    new_blocks = []
    if split_line_idx >= len(block.lines):
        return [block]
    elif split_line_idx == 0:
        return [block]
    else:
        new_blocks.append(Block(lines=block.lines[:split_line_idx], bbox=bbox_from_lines(block.lines[:split_line_idx]), pnum=block.pnum))
        new_blocks.append(Block(lines=block.lines[split_line_idx:], bbox=bbox_from_lines(block.lines[split_line_idx:]), pnum=block.pnum))
    return new_blocks


def find_insert_block(blocks: List[Block], bbox):
    """find insert block"""
    nearest_match = None
    match_dist = None
    for idx, block in enumerate(blocks):
        try:
            dist = math.sqrt((block.bbox[1] - bbox[1]) ** 2 + (block.bbox[0] - bbox[0]) ** 2)
        except Exception as e:
            continue

        if nearest_match is None or dist < match_dist:
            nearest_match = idx
            match_dist = dist
    if nearest_match is None:
        return 0
    return nearest_match


