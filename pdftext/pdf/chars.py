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

import math
from typing import Dict, List
from loguru import logger

import pypdfium2.raw as pdfium_c

from src.pdftext.pdf.utils import get_fontname, pdfium_page_bbox_to_device_bbox, page_bbox_to_device_bbox
from src.pdftext.settings import settings



def update_previous_fonts(char_infos: List, i: int, prev_fontname: str, 
                        prev_fontflags: int, text_page, fontname_sample_freq: int):
    """update previous fonts"""
    min_update = max(0, i - fontname_sample_freq) # Minimum index to update
    for j in range(i - 1, min_update, -1): # Goes from i to min_update
        fontname, fontflags = get_fontname(text_page, j)

        # If we hit the region with the previous fontname, we can bail out
        if fontname == prev_fontname and fontflags == prev_fontflags:
            break
        char_infos[j]["font"]["name"] = fontname
        char_infos[j]["font"]["flags"] = fontflags


def fullwidth_to_halfwidth(text):
    """ Create a translation table """
    fullwidth = ''.join(chr(i) for i in range(0xFF01, 0xFF5E))  # Full-width characters
    halfwidth = ''.join(chr(i) for i in range(0x21, 0x7E))  # Corresponding half-width characters
    translation_table = str.maketrans(fullwidth, halfwidth)
    return text.translate(translation_table)


def get_pdfium_chars(pdf, page_range, fontname_sample_freq=settings.FONTNAME_SAMPLE_FREQ):
    """get pdfium chars"""
    blocks = []
    font_names = set()
    #num_unicode_map_error = 0
    font_info_error = 0
    char_nums = 0
    for page_idx in page_range:
        page = pdf.get_page(page_idx)
        text_page = page.get_textpage()
        mediabox = page.get_mediabox()

        page_rotation = page.get_rotation()
        bbox = page.get_bbox()
        left, bottom, right, top = bbox
        cropbox = page.get_cropbox()

        page_width = math.ceil(abs(bbox[2] - bbox[0]))
        page_height = math.ceil(abs(bbox[1] - bbox[3]))
        bbox = pdfium_page_bbox_to_device_bbox(page, bbox, page_width, page_height, page_rotation)

        # Recalculate page width and height with new bboxes
        page_width = math.ceil(abs(bbox[2] - bbox[0]))
        page_height = math.ceil(abs(bbox[1] - bbox[3]))

        # Flip width and height if rotated
        if page_rotation == 90 or page_rotation == 270:
            page_width, page_height = page_height, page_width

        #bl_origin = (left == 0 and bottom == 0)
        bl_origin = (mediabox[0] == 0 and mediabox[1] == 0)

        text_chars = {
            "page": page_idx,
            "rotation": page_rotation,
            "bbox": bbox,
            "width": page_width,
            "height": page_height,
        }

        fontname = None
        fontflags = None
        total_chars = text_page.count_chars()
        char_nums += total_chars
        char_infos = []
        
        for i in range(total_chars):
            char = pdfium_c.FPDFText_GetUnicode(text_page, i)
            try:
                char = chr(char)
            except Exception as e:
                logger.warning(e)
                continue
            char = fullwidth_to_halfwidth(char)

            fontsize = round(pdfium_c.FPDFText_GetFontSize(text_page, i), 1)
            fontweight = round(pdfium_c.FPDFText_GetFontWeight(text_page, i), 1)
            if fontname is None or i % fontname_sample_freq == 0:
                prev_fontname = fontname
                prev_fontflags = fontflags
                fontname, fontflags = get_fontname(text_page, i)

                font_names.add(fontname)
                if (fontname != prev_fontname or fontflags != prev_fontflags) and i > 0:
                    update_previous_fonts(char_infos, i, prev_fontname, prev_fontflags,
                                         text_page, fontname_sample_freq)

            rotation = pdfium_c.FPDFText_GetCharAngle(text_page, i)
            rotation = rotation * 180 / math.pi # convert from radians to degrees

            coords = text_page.get_charbox(i, loose=rotation == 0) # Loose doesn't work properly when charbox is rotated
            device_coords = page_bbox_to_device_bbox(page, coords, page_width,
                                                 page_height, bl_origin,
                                                page_rotation, normalize=True)

            char_info = {
                "font": {
                    "size": fontsize,
                    "weight": fontweight,
                    "name": fontname,
                    "flags": fontflags
                },
                "fontname": fontname,
                "rotation": rotation,
                "char": char,
                "bbox": device_coords,
                "char_idx": i
            }
            char_infos.append(char_info)

        text_chars["chars"] = char_infos
        text_chars["total_chars"] = total_chars
        blocks.append(text_chars)
    logger.info(f"fonts : {font_names}")
    return blocks