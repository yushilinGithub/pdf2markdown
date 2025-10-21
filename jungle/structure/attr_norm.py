#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
对文本的名称进行归一化，暂且先用 vis 的，后面添加的 html， epub 等也会用这个做归一化，用来做标题层级的识别
"""



import enum

  
class AttrNorm(enum.Enum):  
    """
    ElementAttr，text 中的元素属性
    """
    FIRST_LEVEL_TITLE = "doc_title" 
    SECOND_LEVEL_TITLE = "text_title" 
    PARA = "text"
    TABLE_TITLE = "table_title"
    TABLE = "table"
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_title"
    HEADER = "header"
    FOOTER = "footer"
    FOOTER_NOTE = "footnote"
    CATELOG = "content"
    UNKNOWN = "unknown"

    




  
    