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

import os.path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """setting"""
    MODEL_PATH: str = "src/checkpoints/pdf_extraction/dt.joblib"


    # Fonts
    FONTNAME_SAMPLE_FREQ: int = 1
    # Inference
    BLOCK_THRESHOLD: float = 0.8 # Confidence threshold for block detection
    WORKER_PAGE_THRESHOLD: int = 10 # Min number of pages per worker in parallel

    # Benchmark
    RESULTS_FOLDER: str = "results"
    BENCH_DATASET_NAME: str = "vikp/pdf_bench"


settings = Settings()
