#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
doc string
"""

import yaml

config = yaml.safe_load(open("./conf/01bot.yaml"))
# ES
DOC_ES_HOST = config["mdocai_01bot_doc"].get("DOC_ES_HOST", "")
DOC_ES_PORT = config["mdocai_01bot_doc"].get("DOC_ES_PORT", "")
DOC_ES_USERNAME = config["mdocai_01bot_doc"].get("DOC_ES_USERNAME", "")
DOC_ES_PASSWORD = config["mdocai_01bot_doc"].get("DOC_ES_PASSWORD", "")
DOC_ES_INDEX = config["mdocai_01bot_doc"].get("DOC_ES_INDEX", "")
DOC_LABEL_INDEX = config["mdocai_01bot_doc"].get("DOC_LABEL_INDEX", "")

# VECTOR
VECTOR_SERVER_URL = config["mdocai_01bot_doc"].get("VECTOR_SERVER_URL", "")

# model
SHOULD_PARSE_TABLE = config["ocr_server"].get("SHOULD_PARSE_TABLE", False)
SHOULD_MATCH_TABLE_TO_PARA = config["ocr_server"].get("SHOULD_PARSE_TABLE", False)
DEVICE = config["ocr_server"].get("DEVICE", "cpu")
CPU_LAYOUT_MODEL_PATH = config["ocr_server"].get("CPU_LAYOUT_MODEL_PATH", "src/checkpoints/cpu_layout/model_final.pth")
GPU_LAYOUT_MODEL_PATH = config["ocr_server"].get("GPU_LAYOUT_MODEL_PATH", 
                                                    "src/checkpoints/gpu_layout/layout_model_v0.12.pth")
# GPU_LAYOUT_MODEL_PATH = config["ocr_server"].get("GPU_LAYOUT_MODEL_PATH", 
#     "/home/disk1/yushilin/code/parser/experiment/detrex/output/dino_swin_small_224_4scale_12ep_wen_paper/model_0039999.pth")
READING_ORDER_MODEL_PATH = config["ocr_server"].get("READING_ORDER_MODEL_PATH", "src/checkpoints/reading_order/")
OCR_MODEL_PATH = config["ocr_server"].get("OCR_MODEL_PATH", "src/checkpoints/surya_rec2")
#OCR_MODEL_PATH = config["ocr_server"].get("OCR_MODEL_PATH", 
#    "/home/disk1/yushilin/code/parser/experiment/baidu/personal-code/shilin_ocr/checkpoints/checkpoint-22000")
LINE_DETECTION_MODEL_PATH = config["ocr_server"].get("LINE_DETECTION_MODEL_PATH", "src/checkpoints/line_detection/")
TABLE_MODEL_PATH = config["ocr_server"].get("TABLE_MODEL_PATH", "src/checkpoints/table/")
PDF_EXTRACTION_MODEL = config["ocr_server"].get("PDF_EXTRACTION_MODEL_PATH", "src/checkpoints/pdf_extraction/dt.joblib")


jieba_user_dict = "src/checkpoints/dict/map/jieba_user_dict.txt"
spacy_user_dict = "src/checkpoints/dict/map/spacy_user_dict.txt"

# PG
PG_HOST = config["mdocai_01bot_doc"].get("PG_HOST", "")
PG_PORT = config["mdocai_01bot_doc"].get("PG_PORT", "")
PG_DATABASE = config["mdocai_01bot_doc"].get("PG_DATABASE", "")
PG_USERNAME = config["mdocai_01bot_doc"].get("PG_USERNAME", "")
PG_PASSWORD = config["mdocai_01bot_doc"].get("PG_PASSWORD", "")

CDSS_SERVER_URL = config["mdocai_01bot_doc"].get("CDSS_SERVER_URL", "")
# model
