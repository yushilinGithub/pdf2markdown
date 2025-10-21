#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
batch layout detection.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional
from PIL import Image
import numpy as np

from src.rock.detection import batch_detection
from src.rock.postprocessing.heatmap import keep_largest_boxes, get_and_clean_boxes, get_detected_boxes
from src.rock.schema import LayoutResult, LayoutBox, TextDetectionResult
import src.config_util as settings


def batch_layout_detection(images: List, predictor, batch_size=6) -> List[LayoutResult]:
    """
    batch layout detection.
    """
    images = [np.asarray(image) for image in images]
    results = predictor(images, batch_size=batch_size)
    return results


def batch_table_recognition(images: List, predictor, batch_size=6) -> List[List[str]]:
    """
    batch table recognition.
    """
    images = [np.asarray(image) for image in images]
    results = predictor(images, batch_size=batch_size)
    return results