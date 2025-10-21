#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
pdf text extraction. modified from marker 

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""

import os
from typing import List, Optional, Dict
from loguru import logger 

import pypdfium2 as pdfium
import pypdfium2.internal as pdfium_i

from src.jungle.pdf.utils import font_flags_decomposer
from src.jungle.settings import settings
from src.jungle.schema.block import Span, Line, Block
from src.jungle.schema.page import Page
from src.pdftext.extraction import dictionary_output
from src.jungle.pdf.images import render_image 

os.environ["TESSDATA_PREFIX"] = settings.TESSDATA_PREFIX


def pdftext_format_to_blocks(page, pnum: int) -> Page:
    """
    将pdf文本格式的页面数据转化为blocks的页面数据。
    
    Args:
        page (dict): pdftext格式页面数据。
        pnum (int): 页面页码。
    
    Returns:
        Page: 转化后的blocks格式页面数据。
    
    """

    page_blocks = []
    span_id = 0
    for block_idx, block in enumerate(page["blocks"]):
        block_lines = []
        for l in block["lines"]:
            spans = []
            for i, s in enumerate(l["spans"]):
                block_text = s["text"]
                # Remove trailing newlines and carriage returns (tesseract)
                while len(block_text) > 0 and block_text[-1] in ["\n", "\r"]:
                    block_text = block_text[:-1]

                block_text = block_text.replace("-\n", "") # Remove hyphenated line breaks
                span_obj = Span(
                    chars=s["chars"],
                    rotation=s["rotation"],
                    text=block_text, # Remove end of line newlines, not spaces
                    bbox=s["bbox"],
                    span_id=f"{pnum}_{span_id}",
                    font=f"{s['font']['name']}_{font_flags_decomposer(s['font']['flags'])}",
                    font_weight=s["font"]["weight"],
                    font_size=s["font"]["size"],
                )
                spans.append(span_obj)  # Text, bounding box, span id
                span_id += 1
            line_obj = Line(
                spans=spans,
                bbox=l["bbox"],
            )
            # Only select valid lines, with positive bboxes
            if line_obj.area >= 0:
                block_lines.append(line_obj)
        block_obj = Block(
            lines=block_lines,
            bbox=block["bbox"],
            pnum=pnum
        )
        # Only select blocks with lines
        if len(block_lines) > 0:
            page_blocks.append(block_obj)

    page_bbox = page["bbox"]
    page_width = abs(page_bbox[2] - page_bbox[0])
    page_height = abs(page_bbox[3] - page_bbox[1])
    rotation = page["rotation"]

    # Flip width and height if rotated
    if rotation == 90 or rotation == 270:
        page_width, page_height = page_height, page_width

    char_blocks = page["blocks"]
    page_bbox = [0, 0, page_width, page_height]
    out_page = Page(
        blocks=page_blocks,
        pnum=page["page"],
        bbox=page_bbox,
        rotation=rotation,
        char_blocks=char_blocks
    )
    return out_page


def get_text_blocks(doc, fname, max_pages: Optional[int] = None, 
                    start_page: Optional[int] = None) -> (List[Page], Dict):
    """
    从PDF文档中提取文本块并返回文本块列表以及目录信息。
    
    Args:
        doc: PDF文档对象。
        fname: PDF文档的文件名。
        max_pages: 可选参数，最多处理的页面数。
        start_page: 可选参数，开始处理的页面索引。
    
    Returns:
        包含两个元素的元组：
            - List[Page]: 文本块列表，每个元素表示一个页面上的文本块。
            - Dict: 目录信息，以字典形式表示。
    
    """
    toc = get_toc(doc)

    if start_page:
        assert start_page < len(doc)
    else:
        start_page = 0

    if max_pages:
        if max_pages + start_page > len(doc):
            max_pages = len(doc) - start_page
    else:
        max_pages = len(doc) - start_page

    page_range = range(start_page, start_page + max_pages)

    char_blocks = dictionary_output(fname, page_range=page_range, keep_chars=True, workers=settings.PDFTEXT_CPU_WORKERS)
    jungle_blocks = [pdftext_format_to_blocks(page, pnum) for pnum, page in enumerate(char_blocks)]
    logger.info(f"render image begin")
    for page in jungle_blocks:
        page.page_image = render_image(doc[page.pnum], dpi=settings.IMAGE_DPI)
    logger.info(f"rendered image finish!")
    return jungle_blocks, toc


def naive_get_text(doc):
    """naive get pdf text"""
    full_text = ""
    for page_idx in range(len(doc)):
        page = doc.get_page(page_idx)
        text_page = page.get_textpage()
        full_text += text_page.get_text_bounded() + "\n"
    return full_text


def get_toc(doc, max_depth=15):
    """get toc"""
    toc = doc.get_toc(max_depth=max_depth)
    toc_list = []
    for item in toc:
        list_item = {
            "title": item.title,
            "level": item.level,
            "is_closed": item.is_closed,
            "n_kids": item.n_kids,
            "page_index": item.page_index,
            "view_mode": pdfium_i.ViewmodeToStr.get(item.view_mode),
            "view_pos": item.view_pos,
        }
        toc_list.append(list_item)
    return toc_list


def get_length_of_text(fname: str) -> int:
    """get length of text"""
    doc = pdfium.PdfDocument(fname)
    text = naive_get_text(doc).strip()

    return len(text)
