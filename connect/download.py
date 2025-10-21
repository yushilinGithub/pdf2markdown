#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
download.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""
import requests
from loguru import logger


def download(url):
    """
    download
    """
    req = requests.get(url)
    if req.status_code != 200:
        logger.warning(f'url: {url}\ncode:{req.status_code}, status: 下载异常')
        return None
    else:
        logger.info(f'url: {url}\nstatus: 下载成功')
        return req.content