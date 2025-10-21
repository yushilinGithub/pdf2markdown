#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
logger.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""


import logging
import warnings


def configure_logging():
    """logger convig"""
    logging.basicConfig(level=logging.WARNING)

    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    logging.getLogger('PIL').setLevel(logging.ERROR)
    logging.getLogger('fitz').setLevel(logging.ERROR)
    logging.getLogger('ocrmypdf').setLevel(logging.ERROR)
    warnings.simplefilter(action='ignore', category=FutureWarning)
