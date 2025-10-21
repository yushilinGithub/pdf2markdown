#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
Setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import pypdfium2.raw as pdfium_c
import ctypes
import math
from loguru import logger


LINE_BREAKS = ["\n", "\u000D", "\u000A"]
TABS = ["\t", "\u0009", "\x09"]
SPACES = [" ", "\ufffe", "\uFEFF", "\xa0"]
WHITESPACE_CHARS = ["\n", "\r", "\f", "\t", " "]


def unnormalize_bbox(bbox, page_width, page_height):
    """
    unnormalize bbox
    """
    x1 = round(bbox[0] * page_width, 1)
    y1 = round(bbox[1] * page_height, 1)
    x2 = round(bbox[2] * page_width, 1)
    y2 = round(bbox[3] * page_height, 1)
    return x1, y1, x2, y2


def get_fontname(textpage, char_index):
    """
    get font name
    """
    n_bytes = pdfium_c.FPDFText_GetFontInfo(textpage, char_index, None, 0, None)
    buffer = ctypes.create_string_buffer(n_bytes)
    # Re-interpret the type from char to unsigned short as required by the function
    buffer_ptr = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ushort))
    flag_buffer = ctypes.c_int()
    font_info = pdfium_c.FPDFText_GetFontInfo(textpage, char_index, buffer_ptr, n_bytes, flag_buffer)
    if font_info == 0:
        return None, None
    try:
        decoded = buffer.value.decode("utf-8")
    except Exception as e:
        decoded = buffer.value.decode("gbk")
        #logger.info("font name decode error, decode as gbk")
    return decoded, flag_buffer.value


def page_to_device(page, x, y, page_width, page_height, page_rotation: int):
    """
    Convert PDF coordinates to device coordinates.
    """
    if page_rotation == 90:
        page_rotation = 1
    elif page_rotation == 180:
        page_rotation = 2
    elif page_rotation == 270:
        page_rotation = 3
    else:
        page_rotation = 0
    width = math.ceil(page_width)
    height = math.ceil(page_height)
    device_x = ctypes.c_int()
    device_y = ctypes.c_int()
    pdfium_c.FPDF_PageToDevice(page, 0, 0, width, height, page_rotation, x, y, device_x, device_y)
    x = device_x.value
    y = device_y.value
    return x, y


def pdfium_page_bbox_to_device_bbox(page, bbox, page_width, page_height, page_rotation):
    """ convert pdf box to device bbox """
    left_bottom = page_to_device(page, *bbox[:2], page_width, page_height, page_rotation)
    top_right = page_to_device(page, *bbox[2:], page_width, page_height, page_rotation)

    dev_bbox = [left_bottom[0], top_right[1], top_right[0], left_bottom[1]]
    return dev_bbox


def fast_page_bbox_to_device_bbox(page, bbox, page_width, page_height):
    """
    fast version to convert pdf box to device bbox
    """
    left, bottom, right, top = bbox

    dev_bbox = [left, page_height-top, right, page_height-bottom]
    return dev_bbox


def page_bbox_to_device_bbox(page, bbox, page_width: int, page_height: int, bl_origin: bool, page_rotation: int, normalize=False):
    """
    use pdfium function to device bbox
    """
    orig_page_height, orig_page_width = page_height, page_width
    if page_rotation in [90, 270]:
        orig_page_height, orig_page_width = page_width, page_height

    # if bl_origin:
    #     bbox = fast_page_bbox_to_device_bbox(page, bbox, page_width, page_height)
    #     if page_rotation > 0:
    #         bbox = rotate_page_bbox(bbox, page_rotation, page_width, page_height)
    # else:
    bbox = pdfium_page_bbox_to_device_bbox(page, bbox, orig_page_width, orig_page_height, page_rotation)
    if page_rotation > 0:
        bbox = rotate_pdfium_bbox(bbox, page_rotation, page_width, page_height)

    if normalize:
        bbox = [bbox[0] / page_width, bbox[1] / page_height, bbox[2] / page_width, bbox[3] / page_height]
    return bbox


def rotate_pdfium_bbox(bbox, angle_deg, width, height):
    """
    rotate bbox by angle
    """
    x1, y1, x2, y2 = bbox
    if angle_deg == 90:
        bbox = [y1, x1, y2, x2]
        bbox = [bbox[2], height - bbox[1], bbox[0], height - bbox[3]]
    elif angle_deg == 180:
        bbox = [x2, y2, x1, y1]
        bbox = [width - bbox[0], height - bbox[1], width - bbox[2], height - bbox[3]]
    elif angle_deg == 270:
        bbox = rotate_pdfium_bbox(bbox, 90, width, height)
        bbox = rotate_pdfium_bbox(bbox, 180, width, height)

    return bbox


def rotate_page_bbox(bbox, angle_deg, width, height):
    """
    rotate bbox by angle
    """
    x1, y1, x2, y2 = bbox
    if angle_deg == 90:
        bbox = [y1, x1, y2, x2]
        bbox = [height - bbox[2], bbox[1], height - bbox[0], bbox[3]]
    elif angle_deg == 180:
        bbox = [x2, y2, x1, y1]
        bbox = [width - bbox[0], height - bbox[1], width - bbox[2], height - bbox[3]]
    elif angle_deg == 270:
        bbox = rotate_page_bbox(bbox, 90, width, height)
        bbox = rotate_page_bbox(bbox, 180, width, height)

    return bbox
