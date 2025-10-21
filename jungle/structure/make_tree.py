#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
this file is used to split the markdown into trees recursively, for every title, recursively split it into subtrees.

usage: 
    if you want to split the markdown into trees, you can use this file.
    a markdown file is like this:
    # 一级标题
     content1
    ## 二级标题
     content2
    ### 三级标题
     content3


    then you can use this file to split the markdown into trees.

    the output is like this:
    {"title": 一级标题, 
    "text_span":[0, len(text length of all content in 一级标题)], 
    "text_length": len(content1), 
    "section": 
        [
            content1,
            {
                "title": 二级标题, 
                "text_span":[0, len(...)], 
                "text_length": len(...), 
                "section": 
                    [
                        content2,
                        {
                            "title": 三级标题, 
                            "text_span":[0, len(...)], 
                            "text_length": len(...), 
                            "section": content3
                        {
                    ]
            }
        ]
    }
"""

import re
import json
from typing import List, Dict, Union


split_re_list = ["\n#{==} [^#].+".replace("==", str(i)) for i in range(1, 9)]


def metch_title(text: str, split_turn: int) -> int:
    """
    查询第几级标题，如果没有match到，则返回
    input:
        text: 文本
        split_turn: 当前递归的深度
    output:
        返回一个整数，表示匹配到的标题的级别，如果没有匹配到，则返回-1
    """
    for i in range(split_turn, len(split_re_list)):
        title_re = re.compile(split_re_list[i])
        if title_re.search(text):
            return i
    return -1


def split_text(text: str, split_turn: int, parent_interval: List) -> Union[str, List[Dict]]:
    """
    用递归的方法进行文本的chunk，先把文段解析成字典的形式，字典最大的深度是配置的split_re_list中list的长度。
    input:
        text: 文本
        split_turn: 当前递归的深度
        parent_interval: 当前文本的起始位置和结束位置
    output:
        返回一个字典，字典的最大深度是配置的split_re_list中list的长度。
    """
    if split_turn == len(split_re_list):
        return text
    tree = []
    
    matched_split_index = metch_title(text, split_turn)
    
    if matched_split_index != -1:
        title_re = re.compile(split_re_list[matched_split_index]) 
        title_interval = [[interval.start(), interval.end()] for interval in title_re.finditer(text)] # -1 表示title中不包含末尾的换行符号
        content_interval = sum(title_interval, [])[1:] + [len(text)]
        if title_interval[0][0] != 0:  # 此标题到其下一级标题之间有更细标题。
            result =  split_text(text[0: title_interval[0][0]], 
                                split_turn, 
                                [parent_interval[0], 
                                parent_interval[0]+title_interval[0][0]])  

            if isinstance(result, list):
                tree.extend(result)
            else:
                if result.strip():   
                    tree.append(result)
                        
        for i, ti in enumerate(title_interval):
            data = {"title": text[ti[0]: ti[1]], 
                    "text_span": [parent_interval[0] + content_interval[i * 2], 
                                        parent_interval[0] + content_interval[i * 2 + 1]],   
                    "text_length":  content_interval[i * 2 + 1] -  content_interval[i * 2],   
                                                
                    "section": split_text(text[content_interval[i * 2]: content_interval[i * 2 + 1]], 
                                            split_turn + 1, 
                                            [parent_interval[0] + content_interval[i * 2], 
                                            parent_interval[0] + content_interval[i * 2 + 1]])
                                            }
            if isinstance(data["section"], str) and not data["section"].strip():
                data = data["title"].strip().lstrip("#")
            tree.append(data)
        return tree

    else:

        return text


def md2tree(text: str, filename: str) -> Dict:
    """
    解析md文件，返回一个字典
    input:
        text: markdown 格式的文本
        filename: 文件名
    output:
        result: 字典 {"title": drugname, "text_span":[0, len(text)], "text_length": len(text), "section": tree}
    """
    if not text.startswith("\n"):
        text = "\n" + text
    tree = split_text(text, 0, [0, len(text)])
    result = {"title": filename, "text_span": [0, len(text)], "text_length": len(text), "section": tree}
    return result
