#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
simple recognize document type, guideline paper, drug instruction, etc.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import enum

from typing import List, Dict
from dataclasses import dataclass


@enum.unique
class GuidelineEntities(str, enum.Enum):
    """
    段落属性
    """
    CHINESE_ABSTRACT: str = "chinese_abstract"
    ENGLISH_ABSTRACT: str = "english_abstract"
    CHINESE_KEYWORD: str = "chinese_keyword"
    ENGLISH_KEYWORD: str = "english_keyword"
    ENGLISH_TITLE: str = "english_title"
    CHINESE_AUTHOR: str = "chinese_author"
    ENGLISH_AUTHOR: str = "english_author"
    AUTHOR:str = "author"
    DOI: str = "doi"
    PROJECT_FUNDING: str = "project_funding"


@enum.unique
class ParagraphAttribute(str, enum.Enum):
    """
    段落属性
    """
    UNKNOWN = ''
    DOC_TITLE = 'doc_title'
    TEXT_TITLE = 'text_title'
    TABLE_TITLE = 'table_title'
    TEXT = 'text'

    
@enum.unique
class ParseStatus(int, enum.Enum):
    """
    解析状态
    """
    PREPARE = 0
    PROCESSING = 1
    SUCCESS = 2
    FAILED = 3
    

@enum.unique
class FileType(str, enum.Enum):
    """
    文件类型
    """
    PDF = 'PDF'
    TIFF = 'TIFF'
    XPS = 'XPS'
    CBZ = 'CBZ'
    EPUB = 'EPUB'
    

@enum.unique
class DocType(str, enum.Enum):
    """
    文档类型
    """
    MEDICAL_DOC = '医疗文档'


@enum.unique
class KnowledgeType(str, enum.Enum):
    """
    知识类型
    """
    GUIDELINE = "guideline"
    DRUG_INSTRUCTION = "drug_instruction"
    BOOK = "book"
    UNKNOWN = "unknown"


@enum.unique
class Language(str, enum.Enum):
    """
    语言
    """
    CHINESE = 'chinese'
    ENGLISH = 'english'
    OTHER = 'other'
    GARBAGE = 'garbage'
    UNKNOWN = 'unknown'


@enum.unique
class FragmentStatus(int, enum.Enum):
    """
    文档片段状态
    """
    UNKNOWN = 0 # 未知状态
    ENABLED = 1 # 启用
    DISABLED = 2 # 停用


@dataclass
class ParagraphInfo():
    """
    ParagraphInfo
    """

    book_id: str
    page_id: int 
    evidence_id: str
    evidence_type: str
    book_name: str
    page_content: str
    page_content_ch: str
    fragment_status: int
    titles: List[str]
    attribute: str
    para_idx: List[Dict]
    is_ocr_result: bool