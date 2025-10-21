#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
simple recognize document type, guideline paper, drug instruction, etc.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import sys
import re
from src.jungle.schema.entity import KnowledgeType, Language
from src.jungle.schema.page import Page
from typing import Union, BinaryIO, List


class DocumentType(object):
    """s
    doc type
    """
    def __init__(self, pages: List[Page]):
        """
            初始化PDF文件对象，可选传入文件字节流。如果没有传入，则将文件类型设置为未知，语言设置为中文。
        
        Args:
            file_bytes (Union[bytes, None], optional): PDF文件字节流，默认None. Defaults to None.
        """
        self.DRUG_INSTRUCTION_PATTERN = [r"【药品名称】", r"【成份】", r"【性状】", r"【适应症】", r"【规格】", r"【用法用量】"]
        self.GUIDELINE_PATTERN = [r"^([［【\[][摘提]要[】］\]]\s*|摘要：|摘要目的：)",
                                     r"(通讯作者[;:：]|通信作者[;:：]|通讯作者邮箱[;:：]|通信作者单位[;:：])",
                                     r"基金项目",
                                     r"文献标识",
                                     r"中[国图]分类号",
                                     r"文章编号",
                                     r"专家共识|指南",
                                     r"(DOI[;:：]|doi[;:：]|Doi[;:：])", 
                                     r"[【\[]?\s*(Abstract|ABSTRACT)\s*(OBJECTIVE|Objective)?\s*[】\]:：；]", 
                                     r"([［【\[]关键词[】］\]]|关键词：)",
                                     r"([［【\[]\s*Key\s*words\s*[】］\]]|Key\s*words[:;：])"] 
        self.language = None


        self.document_type = self.get_type(pages)



    def is_possible_drug_instruction(self, text: str) -> bool:
        """
        check if it is drug instruction
        """
        num_exist = 0
        for pattern in self.DRUG_INSTRUCTION_PATTERN:
            if re.search(pattern, text):
                num_exist += 1
        if num_exist >= 3:
            return True


    def is_possible_guideline(self, text: str) -> bool:
        """
        check if it is guideline
        """

        num_exist = 0
        for pattern in self.GUIDELINE_PATTERN:
            if re.search(pattern, text):

                num_exist += 1
        if num_exist >= 2:
            return True


    def get_type(self, pages: List[Page]) -> KnowledgeType:
        """
        get document type, 并且判断输入的语言
        """
        def count_english_characters(text):
            #计算包含多少英文字符
            count = sum(1 for char in text if char.isalpha() and char.isascii())
            return count

        
        def count_chinese_characters(text):
            chinese_count = len(re.findall(r'[\u4e00-\u9fa5]', text))
            return chinese_count

        first_n_page = 5
        
        first_n_page = min(first_n_page, len(pages))
        text = ""
        for i in range(first_n_page):
            text += pages[i].prelim_text

        num_english = count_english_characters(text)
        num_chinese = count_chinese_characters(text)

        num_char = len(text)

        if num_char == 0:  #如果从 PDF 中读取不到text，则人卫是扫描版的书籍

            self.language = Language.CHINESE.value
            return KnowledgeType.UNKNOWN.value

        if num_english / num_char > 0.9:
            self.language = Language.ENGLISH.value

        elif num_chinese > 10:
            self.language = Language.CHINESE.value

        else:
            self.language = Language.GARBAGE.value

        if self.is_possible_drug_instruction(text):
            return KnowledgeType.DRUG_INSTRUCTION.value

        if self.is_possible_guideline(text):
            return KnowledgeType.GUIDELINE.value

        return KnowledgeType.BOOK.value


    def __str__(self):
        """
            返回一个字符串，包含文档类型和语言。
        该方法被 str() 函数调用，以将 DocumentTypeAndLanguage 对象转换为字符串。
        
        Returns:
            str -- 一个字符串，包含文档类型和语言。格式为 "document type: <document_type>, language: <language>"。
        """
        return f"document type: {self.document_type}, language: {self.language}"

