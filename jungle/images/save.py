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

from typing import List

from src.jungle.schema.page import Page


def get_image_filename(page: Page, image_idx):
    """get image file name """
    return f"{page.pnum}_image_{image_idx}.png"


def images_to_dict(pages: List[Page]):
    """images to dict"""
    images = {}
    for page in pages:
        if page.images is None:
            continue
        for image_idx, image in enumerate(page.images):
            image_filename = get_image_filename(page, image_idx)
            images[image_filename] = image
    return images
