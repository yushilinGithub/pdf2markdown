#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
text line detction.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from typing import List

from pypdfium2 import PdfDocument
from src.rock.detection import batch_text_detection

from src.jungle.pdf.images import render_image
from src.jungle.schema.page import Page
from src.jungle.settings import settings


def get_batch_size():
    """get batch size"""
    if settings.DETECTOR_BATCH_SIZE is not None:
        return settings.DETECTOR_BATCH_SIZE
    elif settings.TORCH_DEVICE_MODEL == "cuda":
        return 4
    return 4


def line_detection(doc: PdfDocument, pages: List[Page], det_model, batch_multiplier=1):
    """detect text line"""
    processor = det_model.processor
    max_len = min(len(pages), len(doc))
    #images = [render_image(doc[pnum], dpi=settings.SURYA_DETECTOR_DPI) for pnum in range(max_len)]
    images = [page.page_image for page in pages]

    predictions = batch_text_detection(images, det_model, processor, 
                                        batch_size=int(get_batch_size() * batch_multiplier))
    for (page, pred) in zip(pages, predictions):
        page.text_lines = pred




