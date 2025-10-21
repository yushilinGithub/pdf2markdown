#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从段落中提取包含在段落中的标题
@author: 1329239119@qq.com 
"""
import re
import json
import math
from LAC import LAC



class HeaderExtracter():
    """
    从段落中提取标题，如果标题存在，则返回标题，否则返回空字符串
    """
    def __init__(self) -> None:
        """
                初始化函数，初始化了一些变量和对象。
        
        Args:
            None.
        
        Returns:
            None.
        """
        self.inline_title_re_list = [r"^[\[【][\u4e00-\u9fff、]{1,20}[】\]]",
                                     (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\d\u4e00-\u9fffa-zA-Z\s\(\)αβ（）ⅡⅢⅣⅤⅥⅠ"
                                        r"/、，\.,~‑\-]{1,30}[:：;；]"
                                    ),  # 1.1  #id:7
                                    (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\d\u4e00-\u9fffa-zA-Z\s\(\)αβ（）ⅡⅢⅣⅤⅥⅠ"
                                        r"/、，\.,~‑\-]{1,50}[\(（][A-Za-z,‑\-\s]+[）\)]"
                                    ),
                                     (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\d\u4e00-\u9fffa-zA-Z\(\)αβⅡⅢⅣⅤⅥⅠ"
                                        r"（）/、~\-]{2,30}\s"  # 1.1  #id:7
                                     ),
                                    (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\d\u4e00-\u9fffa-zA-Z\s\(\)αβ（）ⅡⅢⅣⅤⅥⅠ"
                                        r"/、，\.,~‑\-]{1,50}[\(（]"
                                    ),
                                     (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\u4e00-\u9fffa-zA-Z\(\)αβⅡⅢⅣⅤⅥⅠ"
                                        r"（）/、~\-]{1,30}[\(（]图\d+\-\d+[）\)]"
                                    ),
                                     (
                                        r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*[\u4e00-\u9fffa-zA-Z\(\)"
                                        r"αβ（）/、~\-\s]{1,30}[①②③④⑤]"
                                    ),  # 1.1  #id:7
                                     r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*.{10}]",  # 1.1  #id:7
                                     r"^\d+\s*[\u4e00-\u9fffa-zA-Z，,\(\)\.\-‑（）/、~\s]{3,30}[:：;；]",
                                     r"^\d+\s*[\u4e00-\u9fffa-zA-Z\(\)\.\-‑（）/、~]{3,30}\s",
                                     r"^[^。！？!?,，]{3,30}[:：;；]", # 1) 哈哈哈哈；(1) 哈哈哈哈；  有冒号的优先级高于没有冒号的
                                     r"^[^。！？!?,，]{1,30}[\(（][A-Za-z,\s\-]+[）\)]", 
                                     r"^[^。！？!?,，\s][\u4e00-\u9fffa-zA-Z\(\)（）/、~\-]{3,30}\s", #  1) 哈哈哈哈；(1) 哈哈哈哈；
                                     r"^[^。！？!?,，]{1,30}[\(（]图\d+\-\d+[）\)]", 
                                     r"^[\u4e00-\u9fffa-zA-Z、,\(\)（）\s\.\d，]{1,30}[。?？！①②③④⑤]", 
                                     r"^[\[【][\u4e00-\u9fff、]{1,20}[】\]]",
                                    ]  #第一篇  、、、
        self.seg = LAC(mode="seg")
        #self.un_meanful_loc = ["m","xc","w","u"]  # 普通名词， 其他专名词，形容词，数量词，人名，方位名词，普通动词，
        self.sure_title = [0, 1, 2, 3, 4, 7]

    def extract(self, element):
        """
        如果content 中包含标题，然后提取出来
        """
        content = element.text
        ## 判断是否包含 inline header
        content = content.strip()
        search_content = content
        for i, re_str in enumerate(self.inline_title_re_list):
            searched = re.search(re_str, search_content.lstrip())
            if searched:
                if searched.span()[1] == len(search_content):
                    return element
                else:

                    extracted_content = content[searched.span()[1]:] if i in self.sure_title else content
                    element.inline_title_extracted = True
                    
                    if i == 3:
                        element.text = searched.group()[:-1] + "\n\n" + extracted_content
                    else:
                        element.text = searched.group() + "\n\n" + extracted_content
                    return element
            
        #如果没有 search 到，进行分词
        seg_result = self.seg.run(search_content)


        # 提取前5个 token
        append_token = []
        append_pos = []
        meanful_title = False
        for i, token in zip(range(6), seg_result):
            if token.strip():
                append_token.append(token)

            if token.strip() == "。":
                break

            if len(append_token) == 5:
                break


        content = "".join(seg_result[: i + 1]) + "\n\n" + content
        element.inline_title_extracted = True
        element.text = content

        return element 