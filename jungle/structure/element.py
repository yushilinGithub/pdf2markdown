#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
ocr entity
"""

from src.jungle.structure.attr_norm import AttrNorm
from typing import Union, List
import hashlib 
from src.jungle.schema.block import Span


class Element(object):
    """
    结构中的 element 类
    """
    def __init__(self,
                 text: str,
                 pos: List[int],
                 spans: List[Span],
                 attr: Union[None, AttrNorm] = None, 
                 para_id: Union[None, int] = None,
                 page_id: Union[None, int] = None,
                 catelog_page: bool = False,
                 table_trust: bool = True,
                 lines: Union[list, None] = None):
                
        self.text = text
        self.attr = attr
        self.para_id = para_id
        self.page_id = page_id
        self.title_level = -1
        self.pos = pos
        # 在最后转 markdown 的时候使用informative = True 的 element, 
        # 在进行标题识别的时候，informative = False 的 element 不进行标题识别， 但为 header 的元素会利用策略回捞
        self._informative = True
        if self.attr is not None and self.attr in [AttrNorm.HEADER.value,
                                                    AttrNorm.FOOTER.value,
                                                AttrNorm.FOOTER_NOTE.value]: 
            self._informative = False  
        if self.attr == AttrNorm.TABLE.value:
            self.table_id = f"{self.page_id}-{self.para_id}"
        self.catelog_page = catelog_page
        self.titleRePos = -1
        self.global_index = -1
        self.leafNode = False
        self.meta_name = None

        self.fonts = None
        self.font_sizes = None
        self.fonts_width = None
        # get from pdf
        self.lines = lines
        
        #table
        self.table_caption = None
        self.table_title = None
        self.table_figure_url = None
        self.table_footnote = None
        self.table_trust = True

        #figure
        self.figure_title = None
        self.figure_caption = None
        self.figure_url = None
        self.figure_footnote = None

        self.spans = spans

        self.inline_title_extracted = False
        self.corresponding_medium = []
        

    @property
    def id(self):
        """id"""
        return f"{self.page_id}-{self.para_id}"

    @property
    def informative(self):
        """informatice"""
        return self._informative
    
    @informative.setter  
    def informative(self, value: bool):  
        """informative"""
        self._informative = value  
    
    def __str__(self):
        """
        打印 element 信息
        """
        return f"attr: {self.attr}, para_id: {self.para_id}, page_id: {self.page_id}, \
title_level: {self.title_level}, informative: {self.informative}, \
catelog_page: {self.catelog_page}, text: {self.text}, titleRePos: {self.titleRePos},\
global_index: {self.global_index}, meta_name: {self.meta_name}"

