# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
text recognition。

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from typing import Dict, Optional

from dotenv import find_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings
import torch
import os


class Settings(BaseSettings):
    """setting"""
    # General
    TORCH_DEVICE: Optional[str] = None
    IMAGE_DPI: int = 96

    # Paths
    DATA_DIR: str = "data"
    RESULT_DIR: str = "results"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #FONT_DIR: str = os.path.join(BASE_DIR, "static", "fonts")
    FONT_DIR: str = "font/"  
    MODELS_DIR: str = "/home/disk1/yushilin/code/parser/vikp/parser/models"
    ENABLE_EFFICIENT_ATTENTION: bool = True # Usually keep True, but if you get CUDA errors, setting to False can help



    @computed_field
    def TORCH_DEVICE_MODEL(self) -> str:
        """torch device model"""
        if self.TORCH_DEVICE is not None:
            return self.TORCH_DEVICE

        if torch.cuda.is_available():
            return "cuda"

        if torch.backends.mps.is_available():
            return "mps"

        return "cpu"


    @computed_field
    def TORCH_DEVICE_DETECTION(self) -> str:
        """torch device detection"""
        if self.TORCH_DEVICE is not None:
            # Does not work with mps
            if "mps" in self.TORCH_DEVICE:
                return "cpu"

            return self.TORCH_DEVICE

        if torch.cuda.is_available():
            return "cuda"

        # Does not work with mps
        return "cpu"

    # Text detection
    DETECTOR_BATCH_SIZE: Optional[int] = None # Defaults to 2 for CPU, 32 otherwise
    DETECTOR_MODEL_CHECKPOINT: str = os.path.join(MODELS_DIR, "surya_det3")
    DETECTOR_MATH_MODEL_CHECKPOINT: str = os.path.join(MODELS_DIR, "surya_det_math")
    DETECTOR_BENCH_DATASET_NAME: str = "../../models/doclaynet_bench"
    DETECTOR_IMAGE_CHUNK_HEIGHT: int = 1400 # Height at which to slice images vertically
    DETECTOR_TEXT_THRESHOLD: float = 0.6 # Threshold for text detection (above this is considered text)
    DETECTOR_BLANK_THRESHOLD: float = 0.35 # Threshold for blank space (below this is considered blank)
    DETECTOR_POSTPROCESSING_CPU_WORKERS: int = min(8, os.cpu_count()) # Number of workers for postprocessing

    # Text recognition
    RECOGNITION_MODEL_CHECKPOINT: str = os.path.join(MODELS_DIR, "surya_rec")
    RECOGNITION_MAX_TOKENS: int = 175
    RECOGNITION_BATCH_SIZE: Optional[int] = None # Defaults to 8 for CPU/MPS, 256 otherwise
    RECOGNITION_IMAGE_SIZE: Dict = {"height": 256, "width": 896}
    RECOGNITION_RENDER_FONTS: Dict[str, str] = {
        "all": os.path.join(FONT_DIR, "GoNotoCurrent-Regular.ttf"),
        "zh": os.path.join(FONT_DIR, "GoNotoCJKCore.ttf"),
        "ja": os.path.join(FONT_DIR, "GoNotoCJKCore.ttf"),
        "ko": os.path.join(FONT_DIR, "GoNotoCJKCore.ttf"),
    }
    RECOGNITION_FONT_DL_BASE: str = "https://github.com/satbyy/go-noto-universal/releases/download/v7.0"
    RECOGNITION_BENCH_DATASET_NAME: str = "../../models/rec_bench"
    RECOGNITION_PAD_VALUE: int = 255 # Should be 0 or 255
    RECOGNITION_STATIC_CACHE: bool = False # Static cache for torch compile
    RECOGNITION_ENCODER_BATCH_DIVISOR: int = 2 # Divisor for batch size in decoder

    # Layout

    LAYOUT_CHECKPOINT: str = os.path.join(MODELS_DIR, "layout/model_0024999.pth")

    # Ordering
    ORDER_MODEL_CHECKPOINT: str = os.path.join(MODELS_DIR, "surya_order")
    ORDER_IMAGE_SIZE: Dict = {"height": 1024, "width": 1024}
    ORDER_MAX_BOXES: int = 256
    ORDER_BATCH_SIZE: Optional[int] = None  # Defaults to 4 for CPU/MPS, 32 otherwise
    ORDER_BENCH_DATASET_NAME: str = "../../models/order_bench"

    # Table
    TABLE_STRUCTURE_VOCAB: str = os.path.join(MODELS_DIR, "table/vocab_html.json")
    TABLE_STRUCTURE_MODEL: str = os.path.join(MODELS_DIR, "table/unitable_large_structure.pt")
    TABLE_BBOX_VOCAB: str = os.path.join(MODELS_DIR, "table/vocab_bbox.json")
    TABLE_BBOX_MODEL: str = os.path.join(MODELS_DIR, "table/unitable_large_bbox.pt")

    # Tesseract (for benchmarks only)
    TESSDATA_PREFIX: Optional[str] = None

    @computed_field
    @property
    def MODEL_DTYPE(self) -> torch.dtype:
        """model type"""
        return torch.float32 #if self.TORCH_DEVICE_MODEL == "cpu" else torch.float16


    @computed_field
    @property
    def MODEL_DTYPE_DETECTION(self) -> torch.dtype:
        """model dtype"""
        return torch.float32 #if self.TORCH_DEVICE_DETECTION == "cpu" else torch.float16


    class Config:
        """config"""
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()