#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
settings

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


from typing import Optional, List, Dict, Literal

from dotenv import find_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings
import torch
import os


class Settings(BaseSettings):
    """setting"""
    # General
    TORCH_DEVICE: Optional[str] = None # Note: MPS device does not work for text detection, and will default to CPU
    IMAGE_DPI: int = 96 # DPI to render images pulled from pdf at
    IMAGE_DPI_WORKERS: int = 6 # How many CPU workers to use for image rendering
    EXTRACT_IMAGES: bool = True # Extract images from pdfs and save them
    MODELS_DIR: str = "/home/disk1/yushilin/code/parser/vikp/parser/models"

    @computed_field
    @property
    def TORCH_DEVICE_MODEL(self) -> str:
        """torch device model"""
        if self.TORCH_DEVICE is not None:
            return self.TORCH_DEVICE

        if torch.cuda.is_available():
            return "cuda"

        if torch.backends.mps.is_available():
            return "mps"

        return "cpu"

    INFERENCE_RAM: int = 40 # How much VRAM each GPU has (in GB).
    # How much VRAM to allocate per task (in GB).  Peak marker
    # VRAM usage is around 5GB, but avg across workers is lower.
    VRAM_PER_TASK: float = 4.5 
    # Default language we assume files to be in, should be one of the keys in TESSERACT_LANGUAGES
    DEFAULT_LANG: str = "ch" 

    SUPPORTED_FILETYPES: Dict = {
        "application/pdf": "pdf",
    }

    # Text extraction
    PDFTEXT_CPU_WORKERS: int = 10 # How many CPU workers to use for pdf text extraction

    # Text line Detection
    DETECTOR_BATCH_SIZE: Optional[int] = 12 # Defaults to 6 for CPU, 12 otherwise

    SURYA_DETECTOR_DPI: int = 96
    DETECTOR_POSTPROCESSING_CPU_WORKERS: int = 4

    # OCR
    INVALID_CHARS: List[str] = [chr(0xfffd), "�"]
    # Which OCR engine to use, either "surya" or "ocrmypdf".  Defaults to "ocrmypdf" on CPU, "surya" on GPU.
    OCR_ENGINE: Optional[Literal["rock", "ocrmypdf"]] = "rock" 
    OCR_ALL_PAGES: bool = False # Run OCR on every page even if text can be extracted

    ## Surya
    SURYA_OCR_DPI: int = 96
    RECOGNITION_BATCH_SIZE: Optional[int] = 180 # Batch size for surya OCR defaults to 64 for cuda, 32 otherwise

    ## Tesseract
    OCR_PARALLEL_WORKERS: int = 2 # How many CPU workers to use for OCR
    TESSERACT_TIMEOUT: int = 20 # When to give up on OCR
    TESSDATA_PREFIX: str = ""

    # Texify model
    TEXIFY_MODEL_MAX: int = 384 # Max inference length for texify
    TEXIFY_TOKEN_BUFFER: int = 128 # Number of tokens to buffer above max for texify
    TEXIFY_DPI: int = 96 # DPI to render images at
    TEXIFY_BATCH_SIZE: Optional[int] = None # Defaults to 6 for cuda, 12 otherwise
    TEXIFY_MODEL_NAME: str = os.path.join(MODELS_DIR, "texify2")

    # Layout model
    SURYA_LAYOUT_DPI: int = 96
    BAD_SPAN_TYPES: List[str] = ["Caption", "Footnote", "Page-footer", "Page-header", "Picture"]
    LAYOUT_MODEL_CHECKPOINT: str = os.path.join(MODELS_DIR , "layout/model_0024999.pth")
    BBOX_INTERSECTION_THRESH: float = 0.7 # How much the layout and pdf bboxes need to overlap to be the same

    LAYOUT_BATCH_SIZE: Optional[int] = 24 # Defaults to 12 for cuda, 6 otherwise


    # Orde
    SURYA_ORDER_DPI: int = 96

    ORDER_BATCH_SIZE: Optional[int] = 24  # Defaults to 12 for cuda, 6 otherwise

    ORDER_MAX_BBOXES: int = 255

    # Ray
    RAY_CACHE_PATH: Optional[str] = None # Where to save ray cache
    RAY_CORES_PER_WORKER: int = 1 # How many cpu cores to allocate per worker

    # Debug
    DEBUG: bool = True # Enable debug logging
    DEBUG_DATA_FOLDER: Optional[str] = None
    DEBUG_LEVEL: int = 0 # 0 to 2, 2 means log everything


    @computed_field
    @property
    def CUDA(self) -> bool:
        """cuda"""
        return "cuda" in self.TORCH_DEVICE_MODEL

    @computed_field
    @property
    def MODEL_DTYPE(self) -> torch.dtype:
        """model type"""
        if self.TORCH_DEVICE_MODEL == "cuda":
            return torch.bfloat16
        else:
            return torch.float32


    @computed_field
    @property
    def TEXIFY_DTYPE(self) -> torch.dtype:
        """texify dtype"""
        return torch.float32 if self.TORCH_DEVICE_MODEL == "cpu" else torch.float16


    class Config:
        """config"""
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
