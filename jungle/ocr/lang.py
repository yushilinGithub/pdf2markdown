#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
language process.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from typing import List

from src.rock.languages import CODE_TO_LANGUAGE, LANGUAGE_TO_CODE
from src.rock.model.recognition.tokenizer import _tokenize as lang_tokenize

from src.jungle.ocr.tesseract import LANGUAGE_TO_TESSERACT_CODE, TESSERACT_CODE_TO_LANGUAGE
from src.jungle.settings import settings


def langs_to_ids(langs: List[str]):
    """
    langs to ids
    """
    unique_langs = list(set(langs))
    _, lang_tokens = lang_tokenize("", unique_langs)
    return lang_tokens


def replace_langs_with_codes(langs):
    """
    replace langs with codes
    """
    if settings.OCR_ENGINE == "rock":
        for i, lang in enumerate(langs):
            if lang.title() in LANGUAGE_TO_CODE:
                langs[i] = LANGUAGE_TO_CODE[lang.title()]
    else:
        for i, lang in enumerate(langs):
            if lang in LANGUAGE_TO_CODE:
                langs[i] = LANGUAGE_TO_TESSERACT_CODE[lang]
    return langs


def validate_langs(langs):
    """
    check if langs is valid
    """
    if settings.OCR_ENGINE == "rock":
        for lang in langs:
            if lang not in CODE_TO_LANGUAGE:
                raise ValueError(f"Invalid language code {lang} for rock OCR")
    else:
        for lang in langs:
            if lang not in TESSERACT_CODE_TO_LANGUAGE:
                raise ValueError(f"Invalid language code {lang} for Tesseract")