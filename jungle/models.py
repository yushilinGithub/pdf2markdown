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

from src.rock.model.detection.model import load_model, load_processor
#from texify.model.model import load_model as load_texify_model
#from texify.model.processor import load_processor as load_texify_processor
import src.config_util as cfg
from src.rock.model.recognition.model import load_model as load_recognition_model
from src.rock.model.recognition.processor import load_processor as load_recognition_processor
from src.rock.model.ordering.model import load_model as load_order_model
from src.rock.model.ordering.processor import load_processor as load_order_processor
from src.rock.model.layout.model import load_cpu_model, load_gpu_model
from src.rock.model.table.model import load_table_model


def setup_recognition_model(checkpoint=None, langs=None, device=None, dtype=None):
    """
    load recognition model
    """
    if langs is None:
        langs = ["zh", "en"]
    if checkpoint is None:
        checkpoint = cfg.OCR_MODEL_PATH
    if device:
        rec_model = load_recognition_model(checkpoint=checkpoint, device=device, dtype=dtype)
    else:
        rec_model = load_recognition_model(checkpoint=checkpoint)
    rec_processor = load_recognition_processor(checkpoint=checkpoint)
    rec_model.processor = rec_processor
    return rec_model


def setup_detection_model(device=None, dtype=None):
    """
    load line detection model
    """
    if device:
        model = load_model(checkpoint=cfg.LINE_DETECTION_MODEL_PATH, device=device, dtype=dtype)
    else:
        model = load_model(checkpoint=cfg.LINE_DETECTION_MODEL_PATH)

    processor = load_processor(checkpoint=cfg.LINE_DETECTION_MODEL_PATH)
    model.processor = processor
    return model


def setup_texify_model(device=None, dtype=None):
    """
    load formular recognition model
    """
    if device:
        texify_model = load_texify_model(checkpoint=cfg.TEXIFY_MODEL_NAME, device=device, dtype=dtype)
    else:
        texify_model = load_texify_model(checkpoint=cfg.TEXIFY_MODEL_NAME,
                                             device=cfg.TORCH_DEVICE_MODEL,
                                              dtype=cfg.TEXIFY_DTYPE)
    texify_processor = load_texify_processor()
    texify_model.processor = texify_processor
    return texify_model


def setup_order_model(checkpoint=None, device=None, dtype=None):
    """
    load order model
    """
    if checkpoint is None:
        checkpoint = cfg.READING_ORDER_MODEL_PATH
    if device:
        model = load_order_model(checkpoint=checkpoint, device=device, dtype=dtype)
    else:
        model = load_order_model(checkpoint=checkpoint)
    processor = load_order_processor(checkpoint=checkpoint)
    model.processor = processor
    return model


def load_all_models(langs=None, device=None, dtype=None, force_load_ocr=False):
    """
    load all models
    """
    if device is not None:
        assert dtype is not None, "Must provide dtype if device is provided"
    if device is None:
        device = cfg.DEVICE
    # langs is optional list of languages to prune from recognition MoE model
    detection = setup_detection_model(device, dtype)
    if device == 'cpu':
        layout = load_cpu_model(checkpoint=cfg.CPU_LAYOUT_MODEL_PATH, device=device)
    elif device == 'cuda':
        layout = load_gpu_model(checkpoint=cfg.GPU_LAYOUT_MODEL_PATH, device=device)
    else:
        raise ValueError("Invalid device type")
    order = setup_order_model(checkpoint=cfg.READING_ORDER_MODEL_PATH, device=device, dtype=dtype)
    #edit = load_editing_model(device, dtype)

    # Only load recognition model if we'll need it for all pdfs
    ocr = setup_recognition_model(checkpoint=cfg.OCR_MODEL_PATH, langs=["zh", "en"], device=device, dtype=dtype)

    #texify = setup_texify_model(device, dtype)
    if cfg.SHOULD_PARSE_TABLE:
        table_model = load_table_model(checkpoint=cfg.TABLE_MODEL_PATH, device=device)
    else:
        table_model = None
    model_lst = [layout, order, detection, ocr, table_model]
    return model_lst