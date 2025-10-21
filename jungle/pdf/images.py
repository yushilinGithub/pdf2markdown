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


import pypdfium2 as pdfium
from pypdfium2 import PdfPage

from src.jungle.schema.page import Page
from src.jungle.schema.bbox import rescale_bbox
from src.jungle.settings import settings
from loguru import logger


def render_image(page: pdfium.PdfPage, dpi):
    """render image of pdf"""
    
    # 除掉水印
    # try:
    #     for obj_id, obj in enumerate(page.get_objects(max_depth=5)):

    #         if isinstance(obj, pdfium.PdfImage):
    #             #page.remove_obj(obj)
    #             bitmap = obj.get_bitmap()#.to_pil()

    #             bitmapInfo = bitmap.get_info()
    #             if bitmapInfo.width == 272 and bitmapInfo.height == 316 and bitmapInfo.format == 2:
    #                 logger.info(f"Found watermark {bitmapInfo}")
    #                 page.remove_obj(obj)
    # except Exception as e:
    #     logger.warning(f"Failed to remove watermark: {e}")


    image = page.render(
        scale=dpi / 72,
        draw_annots=False
    ).to_pil()
    image = image.convert("RGB")
    return image


def render_bbox_image(page_obj: PdfPage, page: Page, bbox):
    """render bbox image"""
    png_image = render_image(page_obj, settings.IMAGE_DPI)
    # Rescale original pdf bbox bounds to match png image size
    png_bbox = [0, 0, png_image.size[0], png_image.size[1]]
    rescaled_merged = rescale_bbox(page.bbox, png_bbox, bbox)

    # Crop out only the equation image
    png_image = png_image.crop(rescaled_merged)
    png_image = png_image.convert("RGB")
    return png_image