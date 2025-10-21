#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
pdf text extraction. modified from marker 

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""


from abc import ABC, abstractmethod 
from typing import Union, Dict
import os

from src.jungle.structure.attr_norm import AttrNorm

from .make_tree import md2tree
from .element import Element
from .tree_builder import build_tree


class BaseStructure(ABC):  
    """base structure"""

    def __init__(self, filename: str = None):  
        """
           用来管理文件段落的结构，并提供一些基本的操作。
        
        Args:
            filename (str): 文件的文件名。
        
        Returns:
            None.
        
        Raises:
            None.
        """
        self._data = []
        self.markdown = None


    def __len__(self):  
        """
            返回文件段落的数量。
        
        Returns:
            int: 返回文件段落的数量。
        """
        return len(self._data)  

  
    def __getitem__(self, index):  
        """
            根据索引获取元素，支持整数和切片。
        如果索引为整数，则返回对应位置的元素；如果索引为切片，则返回对应范围内的所有元素。
        如果索引不是整数或切片，则会抛出类型错误。
        
        Args:
            index (int or slice): 索引，可以是整数或切片。
        
        Returns:
            Union[Any, List[Any]]: 如果索引为整数，则返回对应位置的元素；如果索引为切片，则返回对应范围内的所有元素。
            如果索引超出范围，则会抛出IndexError异常。
        
        Raises:
            TypeError: 如果索引不是整数或切片，则会抛出类型错误。
        """
        if isinstance(index, int):  
            if index < 0:  
                index += len(self)  
            if not 0 <= index < len(self):  
                raise IndexError('index out of range')  
            return self._data[index]  
        elif isinstance(index, slice):  
            return self._data[index]
        else:  
            raise TypeError('indices must be integers or slices')  

  
    def __iter__(self):  
        """
            迭代器，返回一个包含所有数据的迭代器。
        该函数必须实现 __iter__() 方法以使得对象可以被用于 for 循环中。
        
        Returns:
            Iterator[Any]: 一个包含所有数据的迭代器。
        """
        return iter(self._data) 

  
    def __str__(self):  
        """
        convert structure to string
        """
        result = ""
        for element in self._data:
            result += str(element) + "\n"
        
        return result.strip() 


    def index(self, element):
        """
        the index time complexity of list is O(n), so save global index in element,
         return global index, time complexity is O(1)
        """
        global_index = element.global_index
        return global_index


    def add(self, element: Element):
        """
        add element to the structure
        """
        assert isinstance(element, Element)
        element.global_index = len(self._data)
        self._data.append(element)
    

    def to_markdown(self) -> str:
        """
        return markdown representation of the structure
        """
        markdown = ""
        for element in self._data:
            if element.informative:
                if element.meta_name is None:
                    markdown += f"{(element.title_level + 1) * '#'} {element.text}\n\n"
                else:
                    markdown += f"{element.text}\n\n"
        self.markdown = markdown.strip()
        return markdown
        
    def to_tree(self, filename) -> Dict:
        """
        return tree representation of the structure
        input: file_name: 
        """
        # convert struture to markdown, but with no meta data, if meta data 
        # is not None, did not add this element to the markdown
        
        result = {"file_name": filename}
        tree = build_tree(self)
        result["json_tree"] = tree
        result["extra_info"] = {}
        for element in self._data:
            if element.informative and element.meta_name is not None:
                if element.meta_name in result["extra_info"]:
                    result["extra_info"][element.meta_name].append(element.text)
                else:
                    result["extra_info"][element.meta_name] = [element.text]
            
            if element.page_id == 0 and element.attr in [AttrNorm.HEADER.value,
                                                        AttrNorm.FOOTER.value,
                                                        AttrNorm.FOOTER_NOTE.value]:

                result["extra_info"][element.attr] = element.text
        
        return result

class PDFStructure(BaseStructure):
    """
    PDF structure
    """
    def __init__(self, file_bytes: Union[bytes, None] = None, file_name: Union[str, None] = None) -> None:
        """
        init
        """

        super().__init__(filename=file_name)


    def add(self, element: Element):
        """
        add element
        """
        assert isinstance(element, Element)
        element.global_index = len(self._data)
        self._data.append(element)
        

    def merge_consecutive_es(self, first_index: int, second_index: int):
        """
        merge two consecutive elements into one, and delete the rest
        """
        assert first_index + 1 == second_index 
        self._data[first_index].text += self._data[second_index].text
        self._data[second_index].informative = False

    def self_title_assign(self):
        """
        assign title level to each element that has no title level assigned
        """
        for i, element in enumerate(self._data):
            if element.attr == "doc_title":
                element.title_level = 1
            elif element.attr == "text_title":
                element.title_level = 2
    
    