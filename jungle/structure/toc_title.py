#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get title from pdf metadata
Author: 1329239119@qq.com
"""

import difflib
import re
import numpy as np
from typing import Union, BinaryIO, List, Dict
from src.jungle.structure.structure import PDFStructure
from loguru import logger


class CatelogUnit:
    """
    pdf 元数据中获取标题
    """

    def __init__(self, level: int, 
                        title: str, 
                        page_id: int, 
                        is_closed: bool, 
                        n_kids: int, 
                        view_mode: int, 
                        view_pos: int):
        """
        获取标题的层级，标题，页码
        """
        self.level = level
        self.title = title
        self.page_id = page_id
        self.is_closed = is_closed
        self.n_kids = n_kids
        self.view_mode = view_mode
        self.view_pos = view_pos
        self.Matched = False
        self.CorrespondingText = None
    

    def __str__(self):
        """
        打印当前的标题
        """
        return f'level: {self.level}, title: {self.title},\
             page_id: {self.page_id}, is_closed: {self.is_closed}, Matched: {self.Matched}, \
                CorrespondingText: {self.CorrespondingText}'


class MetaCateLog:
    """
    pdf 元数据中获取标题
    """
    def __init__(self, toc: List) -> None:
        """
            初始化PDF文档对象。
        
        Args:
            doc (bytes): PDF文档的字节数据，必须是完整的PDF文件。
        
        Returns:
            None: 无返回值，只用于初始化对象。
        """
        self.pdfMetaTitle = self.get_meta_title_from_pdf(toc)


    def get_meta_title_from_pdf(self, toc: List) -> List[CatelogUnit]:
        """
        从PDF文件中提取标题，返回一个列表，每个元素为一个CatelogUnit对象。
        
        Args:
            file_bytes (bytes): PDF文件的字节数组。
        
        Returns:
            List[CatelogUnit]: 一个列表，其中每个元素是一个CatelogUnit对象，包含了标题、页码和深度等信息。
        
        Raises:
            无。
        """
        bookmarks = []
        for item in toc:
            bookmarks.append(CatelogUnit(level=item["level"], title=item["title"],
                                      page_id=item["page_index"], is_closed=item["is_closed"],
                                      n_kids=item["n_kids"], view_mode=item["view_mode"], view_pos=item["view_pos"]))
        return bookmarks


    def __bool__(self) -> bool:
        """
        判断是否从 meta 中获取到标题，至少包含一个标题, 并且标题的页码数要大于1，否则是错乱的标题没有意义
        """
        if len(self.pdfMetaTitle) < 2:
            return False

        for item in self.pdfMetaTitle:
            if item.page_id is None:
                return False

            if item.page_id > 1:
                return True
        
        return False

    
    def assign_title_level(self, structure: PDFStructure) -> Union[str, bool]:
        """
        将从 pdf 中获取到的标题插入到 markdown 中
        """

        unmatched = 0
        for page_id in range(structure.num_pages):
            element_in_page = [element for element in structure if element.page_id == page_id]
            item_in_page = [item for item in self.pdfMetaTitle if item.page_id == page_id]
            
            if len(element_in_page) == 0 or len(item_in_page) == 0:
                continue

            matrix = np.zeros((len(item_in_page), len(element_in_page)))


            for row, item in enumerate(item_in_page):
        
                for col, element in enumerate(element_in_page):
                    ratio = difflib.SequenceMatcher(None, item.title.lower().replace(" ", ""), \
                                                     element.text.lower().replace(" ", "")).ratio() 
                    matrix[row, col] = ratio 
            
            num_max = np.argmax(matrix, axis=1)

            
            for row, item, matched_idx in zip(range(len(item_in_page)), item_in_page, num_max):
                matched = matrix[row, matched_idx] > 0.7
                if matched:
                    item.Matched = True
                    item.CorrespondingText = element_in_page[matched_idx]
                    element_in_page[matched_idx].title_level = item.level
                else:
                    unmatched += 1
        logger.warning(f"unmatched title {unmatched}")
        return structure


    def __str__(self):
        """
        打印 PDF 元数据中的标题
        """
        result = ""
        for item in self.pdfMetaTitle:
            result += f'{item}\n'
        return result
    
