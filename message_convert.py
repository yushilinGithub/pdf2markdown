#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
doc string
"""

import json
import time
from loguru import logger


def http_data_to_file_data(http_data):
    """
    将HTTP请求数据转换为文件数据
    """
    return {"files": http_data.get("data", [])}


def mq_data_to_file_data(mq_data):
    """
    将mq请求数据转换为文件数据
    """
    return {"files": mq_data}