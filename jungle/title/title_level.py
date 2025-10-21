#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author: yushilin@baidu.com
title level recognition
"""


import sys

import os

# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
import re
from src.jungle.title.inline_title_extract import HeaderExtracter
from src.jungle.structure import BaseStructure
from src.jungle.schema.entity import KnowledgeType
from src.jungle.structure.attr_norm import AttrNorm
from src.jungle.structure.element import Element
from src.jungle.title.utils import get_all_character, contain_chinese, count_ch_characters
from typing import Union


class DynamicTitleParser(object):
    """dynamic title level predict"""

    def __init__(self) -> None:
        """
            初始化函数，初始化属性和变量。
        
        Args:
            None.
        
        Returns:
            None.
        """
        self.title_re_list = [
            (
             r"^(第|上|下)((\d+)|(\\math(rm|bf)?\s?(I{0,3})|N|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ)"
             r"|([一二三四五六七八九十][○一二三四五六七八九十]?[一二三四五六七八九十]?))?(篇|部分|讲).{0,50}$"   #第一篇  、、、    id: 0
            ),
            (
             r"^([^\u4e00-\u9fff]{0,4}第((\d+)|([一二三四五六七八九十]"
             r"[○一二三四五六七八九十]?[一二三四五六七八九十]?))?章[^。]{0,50})$"
            ),   #第一章 、、、   id:1
            (
             r"^([^\u4e00-\u9fff]{0,4}第((\d+)|([一二三四五六七八九十][○一二三四五六七八九十]?"
             r"[一二三四五六七八九十]?))?[爷节][^。]{0,70})$"   #第一节 、、、    id:2
            ),
            r"^[一二三四五六÷七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?(([、，。].+)|(.{0,50})$)", # 一、 id:3
            r"^[\[【][\u4e00-\u9fffa-zA-Z、\~\d\-]{1,20}[\]】]", #【xxx】 id:4
            #r"^[\[【](?=.*[\u4e00-\u9fffA-Za-z])[\u4e00-\u9fffa-zA-Z、\~\d\-]{1,20}[\]】]$",
            r"^[\(（][-一二三四五六七八九十(\+\\equiv)][○一二三四五六七八九十]?[○一二三四五六七八九十]?[）\)].+",  # （一）\ id:5
            r"^((\d{1,3}\s*[\.，。﹒、．,\u4e00-\u9fffa-zA-Z]\s*\D.*)|(\d{1,3}\s*[\u4e00-\u9fffa-zA-Z\s\"“《]+))",
            r"^\d{1,3}(\s*[\.﹒．]\s*\d{1,3}){1}\s*(?!\s*[\.﹒．]\s*\d+)+",  # 1.1  #id:7
            r"^\d{1,3}(\s*[\.﹒．]\s*\d{1,3}){2}\s*(?!\s*[\.﹒．]\s*\d+)+",  # 1.1.1  #id:8
            r"^\d{1,3}(\s*[\.﹒．]\s*\d{1,3}){3}\s*(?!\s*[\.﹒．]\s*\d+)+", # 1.1.1.1 #id:9
            r"^\d{1,3}(\s*[\.﹒．]\s*\d{1,3}){4,}\s*(?!\s*[\.﹒．]\s*\d+)+", # 1.1.1.1.1 
            r"^[\(（]\s*\d\d?\d?\s*[）\)].+", #(23)xxx id:11
            r"^[1-9][0-9]?\s*\d?[）\)].+",   #23)xxx id:12
            (
                r"^("
                r"[①②③④⑤⑥⑦⑧⑨⑩ⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅰⅱⅲⅳⅴⅵⅶⅷⅸ"
                r"❶❷❸❹❺❻❼❽❾❿⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴].+|"
                r"[abcdef]\s*[,\.、][\u4e00-\u9fff]+|"
                r"[①②③④⑤⑥⑦⑧⑨⑩ⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
                r"❶❷❸❹❺❻❼❽❾❿⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴]+"
                r"[\u4e00-\u9fffa-zA-Z\s]+"
                r")"
            )
        ] 

        self.book_bracket_pattern = r"^[\[【][\u4e00-\u9fffa-zA-Z、\~\d\-]{1,20}[\]】]" 
        self.lowestHeader = 16
        self.nonMatchedDocHeader = 14
        self.nonMatchedTextHeader = 15
        self.header_extracter = HeaderExtracter()
        self.not_encounter_title_before = True
        self.titleLevelStartSign = [
            r"^(第[一1](篇|部分|讲)[^。]{0,30})",   #第一篇  、、、
            r"^(第[一1]章[^。]{0,30})",   #第一章 、、、  
            r"^(第[一1]节[^。]{0,30})",   #第一节 、、、
            r"^[-一][、，].+", # 一、
            r"^[\(（][-一][）\)].+", #（一）
            r"^1\s*[\.﹒．]?\s*\D+", # 1, 
            r"^1(\s*[\.﹒．]\s*1){1,4}\s*(?!\s*[\.﹒．]\s*\d+)+",  # 1.1.1
            r"^[\(（]1[）\)].+",
            r"^①.+",
        ]
        self.emptyZhangPattern = (
                                    r"^(第|上|下)(\d+|[-一二三四五六七八九十][○-一二三四五六七八九十]?"
                                    r"[○-一二三四五六七八九十]?)?(篇|部分|章|节|讲)[^\u4e00-\u9fffa-zA-Z]?"
                                )
        self.reset()

        self.undefineP = [4]

        self.goBack = [self.nonMatchedDocHeader, self.nonMatchedTextHeader]

        self.whether_title_re_list = [
        r"^(第|上|下)((\d+)|([-一二三四五六∴七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?))?(篇|部分|讲)[^。]{0,30}$",
        r"^(第((\d+)|([-一二三四五六∴七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?))章[^。]{0,30})$",  
        r"^(第((\d+)|([-一二三四五六∴七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?))节[^。]{0,30})$",   #第一节 、、、
        #r"^[一二三四五六七八九十(\\equiv)][○一二三四五六七八九十]?[○一二三四五六七八九十]?[^。；]{1,30}$", # 一、 
        r"^([一二三四五六÷七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?[、，]?|-[,、。\.])[^。；]{1,30}$", # 一、 
        (
        r"^(([〔【][\u4e00-\u9fffa-zA-Z、\~\d\-\(\)]{1,20}[】〕])|"
        r"(\[[\u4e00-\u9fffa-zA-Z、\~\-\(\)]{1,20}\]))$"
        ),
        r"^[\(（][-一二三四五∓六七八九十(\s?\\equiv\s?)][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?[）\)][^。；]{1,30}$",  # （一）
        r"^\d{1,3}\s?[\.，﹒、．,\u4e00-\u9fffa-zA-Z][^。]{1,30}$",
        r"^[\(（][1-9][0-9]?[）\)][^。]{1,30}$",
        r"^[1-9][0-9]?[）\)][^。]{1,30}$",  
        r"^[①②③④⑤⑥⑦⑧⑨⑩ⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅰⅱⅲⅳⅴⅵⅶⅷⅸ❶❷❸❹❺❻❼❽❾❿⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴][^。]{1,50}$",
        ]
        self.notTitle = [
            (
                r"^\d+\s?(\.\d+)*(年|世纪|月|型|期|种|个|岁|根|周|次|条|倍|度|毫升|克|"
                r"毫克|千|万|号|亿|斤|点|分钟|株|项|点|名|组|余位|已经给出|对(?!于)).*"
            ),
                r"^\d+\s?(\.\d+)*(mm|％|cm|m|nm|km|kg|μ|g|mg|倍|元|s|min|h|Hz|%|kb|∼|=|点|°).*",
                r"^20\d\d版.*",
                r"^199\d.*",
                r"^[12]型糖尿病.*",
                r"[\[【]\s*\**(中[国图]分类号|[Dd][Oo][Ii]|Abstract|ABSTRACT|关键词|Keywords|KEYWORDS|摘要|Summary|编者按)\**\s*[\]】]",
            (
                r"^一(切|批|战|线|些|群|点|般|型|部|条|氧|个|种|样|直|天|幅|次|定|边"
                r"|起|战|来|担|旦|路|期|汽|锥状叶|是|侧|致|体化|提到|项|方面|开始|同|系列).*"
            ),
                r"^-\d.*",
                r"^\d+(\.\d+)?(元|年|天|月|小时|\-|\+|\*|➗|÷).*",
                r"^\d+~\d+个.+",
                r"^四(肢|肽|酸|分体|聚体|氯化碳|氢生物|链|体|联体|面体|线).*",
            (
                r"^三(叉脑|战|线|叉神经|链结构|氧|酸循环|羧酸|烯生育|脂肪酰基甘油|联管|丁基|"
                r"磷酸|酸环|尖杉|脑室|尖学说|角嵴|子养亲汤|七|核苷酸|硅酸镁|唑仑|要|不要|系法模式|体|螺旋|叉神经|酯血症).*"
            ),
                r"^二(腹|零|战|线|个|尖瓣|联管|侧|油|氧|战|维码|丁基|棱镜|甲基|乙基|丙基|丁基|胺|巯丙醇|甲双胍|盐酸|硫基|甲苯|型糖尿病).*",
                r"^(十二指肠|六淫|五苓散|十二经脉|二巯基丙醇|一分子|羧酸|一碳单位|五味子|五官科|18-三体综合征|十字|八宝门|五脏|六腑).*",
                r"^[-一二三四五六七八九十○]+[维件亿万千年月天是级大倍日种类个诊代根多名起位点氟氯株位味步氢胎岁下跟周次度升阶段].*",
                r"^[-一二三四五六七八九十○]+(聚体|星级|环|疗程|世纪|房室).*",
                r"^\[[abcdefghijk]\].+",
                r"^\[\s?\d+\s?\].+"
        ]
        self.referencePattern = r"^\[\d+\].+"

        self.ChineseNumber = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九",
                            "二十", "二十一", "二十二", "二十三", "二十四", "二十五", "二十六", "二十七", "二十八", "二十九",
                            "三十", "三十一", "三十二", "三十三", "三十四", "三十五", "三十六", "三十七", "三十八", "三十九",
                            "四十", "四十一", "四十二", "四十三", "四十四", "四十五", "四十六", "四十七", "四十八", "四十九",
                            "五十", "五十一", "五十二", "五十三", "五十四", "五十五", "五十六", "五十七", "五十八", "五十九",
                            "六十", "六十一", "六十二", "六十三", "六十四", "六十五", "六十六", "六十七", "六十八", "六十九",
                            "七十", "七十一", "七十二", "七十三", "七十四", "七十五", "七十六", "七十七", "七十八", "七十九",
                            "八十", "八十一", "八十二", "八十三", "八十四", "八十五", "八十六", "八十七", "八十八", "八十九",
                            "九十", "九十一", "九十二", "九十三", "九十四", "九十五", "九十六", "九十七", "九十八", "九十九",
                            "一百"]

        self.drug_instruction_trigger = r"(【药品名称】|【成份】|【适应症】|【用法用量】|【规格】|【不良反应】|【禁忌】|【注意事项】)"

        self.lowestHeaderPattern = (
                                    r"(要点：|推荐阅读资料|学习目标|病例|要点提示|学习要点|参\s*考\s*文\s*献|参考资料|教学要求|通讯作者|收稿日期"
                                    r"教学内容|阅读文献|关键词|微信扫描|【中图分类号】|Summary|【摘要】|\[摘要\]|"
                                    r"思考题|练习题|分析题|参考书|学生自测题|推荐网站|问题与思考|推荐书目|教学目标|"
                                    r"内容提示|内容提要|知识点|小贴士|临床病例|二至丸|习题|KEY POINTS)"
                                    )

        self.gobackStopMetaSign = ["chinese_abstract", "english_abstract", "chinese_keyword", "english_keyword"]

        self.ParallelUniverse = [7, 8, 9, 10]
        self.ParentOf = {7: [0, 1, 2, 6], 8: [7], 9: [8], 10: [9]}
        self.sonOf = {7: [8, 9, 10], 8: [9, 10], 9: [10], 10: []}
        self.firstZhangAdded = False
        self.zhangHeaderBegin = 0
        self.addedZhangHeader = []

    
    def reset(self):
        """
        some init parameter changed during predict title level, reset it to original
        """

        self.not_encounter_title_before = True
        self.SuccessorOf = {
            0 : set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                        self.nonMatchedDocHeader, self.nonMatchedTextHeader, self.lowestHeader]),
            1 : set([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 
                        self.nonMatchedDocHeader, self.nonMatchedTextHeader, self.lowestHeader]),
            2 : set([3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                         self.nonMatchedDocHeader, self.nonMatchedTextHeader, self.lowestHeader]),
            3 : set([5, 6, 7, 11, 12, 13, self.lowestHeader]),
            4 : set([13, self.lowestHeader]),
            5 : set([6, 11, 12, 13, self.lowestHeader]),
            6 : set([11, 12, 13, self.lowestHeader]),
            7 : set([8, 9, 10, 11, 12, 13, self.lowestHeader]),
            8 : set([9, 10, 11, 12, 13, self.lowestHeader]),
            9 : set([10, 11, 12, 13, self.lowestHeader]),
            10 : set([11, 12, 13, self.lowestHeader]),
            11 : set([12, 13, self.lowestHeader]),
            12 : set([13, self.lowestHeader]),
            13 : set([self.lowestHeader]),
            self.nonMatchedDocHeader : set([7, 8, 9, 10, 11, 12, 13, 
                                        self.lowestHeader]), #没有标记的 doc_title 
            self.nonMatchedTextHeader : set([7, 8, 9, 10, 11, 12, 13, 
                                        self.lowestHeader]), #没有标记的 text_title
            self.lowestHeader: set([]),
        }
        self.AncestorOf = {
            self.lowestHeader : set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                     self.nonMatchedDocHeader, self.nonMatchedTextHeader]), #参考文献

            self.nonMatchedTextHeader : set([0, 1, 2]), #没有标记的 text_title
            self.nonMatchedDocHeader : set([0, 1, 2]), #没有标记的 doc_title

            13 : set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 
                    self.nonMatchedDocHeader, self.nonMatchedTextHeader]),

            12 : set([0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, self.nonMatchedDocHeader, self.nonMatchedTextHeader]),
            11 : set([0, 1, 2, 3, 5, 6, 7, 8, 9, 10, self.nonMatchedDocHeader, self.nonMatchedTextHeader]),
            10 : set([0, 1, 2, 7, 8, 9]),
            9 : set([0, 1, 2, 7, 8]),
            8 : set([0, 1, 2, 7]),
            7 : set([0, 1, 2]),
            6 : set([0, 1, 2, 3, 5]),
            5 : set([0, 1, 2, 3]),
            4 : set([0, 1, 2]),
            3 : set([0, 1, 2]),
            2 : set([0, 1]),
            1 : set([0]),
            0 : set([]),
        }


    def titleLevelStart(self, title):
        """
            判断标题是否以指定的开头符号开始，如果开头符号存在则返回True，否则返回False。
        默认支持的开头符号包括：'一', '（一）', '①', '（1）', 
        
        Args:
            title (str): 待判断的标题字符串。
        
        Returns:
            bool: 如果标题以指定的开头符号开始，则返回True；否则返回False。
        """
        for startSign in self.titleLevelStartSign:
            if re.search(startSign, title):
                return True
        return False


    def merge_title(self, element, element_index, structure):
        """
        两个标题的 merge 需要达到以下三个条件。
        1，章节后面没有文字
        2，如果章节后面是doc_title, 或者text_title 则直接 merge。
        3，如果章节后面是文本，那么要求这个段落的文本小于12个子。
        """


        if len(structure) < 2:
            return False

        title = element.text
        titleRePos = element.titleRePos
        title =  re.sub(r"<\d+-\d+>", "", title)

        last_element = structure[element_index - 1]
        last_title_RePos = last_element.titleRePos
        last_string = re.sub(r"<\d+-\d+>", "", last_element.text)
        if titleRePos in self.goBack: #如果是text title 或者是 doc title
            if (last_title_RePos == 0 or last_title_RePos == 1) and not re.sub(self.emptyZhangPattern, "", last_string):
                 #如果上一个 element 是篇或者章，并且是篇或者章后面没有任何字符
                structure.merge_consecutive_es(element_index - 1, element_index)

                return True
            else:
                return False
        elif "。" not in title and len(title) < 18 and (titleRePos == -1 or self.notTitleMatched(title)):

            if (last_title_RePos == 0 or last_title_RePos == 1) and not re.sub(
                self.emptyZhangPattern, "", last_string): #如果前面是篇或者章

                structure.merge_consecutive_es(element_index - 1, element_index)
                return True
            else:
                return False
        elif last_title_RePos == 0 and not re.sub(self.emptyZhangPattern, "", last_string) \
                and re.search(r"^第[\d一二三四]部分", last_string): 
            last_element.title_level = -1
            last_element.titleRePos = 14

        else:

            return False


    def getLastHeader(self, element: Element, structure: BaseStructure, eid: int) -> Union[None, Element]:
        """
        找到往前最近的一个标题，如果没有，就返回 None
        """

        for preHeader in structure[:eid][::-1]:
            if preHeader.title_level != -1 and preHeader.informative:
                return preHeader
        return structure[eid - 1]


    def get_title_slot(self, element: Element) -> int:
        """
        匹配 element 所对应的层级当中的 pattern。
        """
        title = element.text
        visattr = element.attr

        title = title.strip()
        title = re.sub(r"<\d+-\d+>", "", title)
        title = title.replace("\\equiv", "三")
        title = title.replace("+\\equiv", "十三")

        if not contain_chinese(title) and re.search(r"=\+\-√≤", title): # must be a equation
            return -1
        
        possibleID = -1

        for patternID, pattern in enumerate(self.title_re_list):
            if re.search(pattern, title): 

                if patternID < 2: #对于第一篇、第一章、第一部分等如果包含的中文字符小于35，那么认为是这个 pattern 的标题。
                    if len(re.sub(r"[A-Za-z]+", "", title)) < 35: 

                        return patternID
                    else:
                        return -1
                possibleID = patternID

        if possibleID in [3, 4, 6]: # 4 for reference like [2] xxx
            if self.notTitleMatched(title):
                if visattr == AttrNorm.SECOND_LEVEL_TITLE.value:
                    return self.nonMatchedTextHeader
                elif visattr == AttrNorm.FIRST_LEVEL_TITLE.value:
                    return self.nonMatchedDocHeader
                else:
                    return -1

            return possibleID

        elif possibleID == 7:
            nonTitleMatched_slot = self.notTitleMatched(title)
            if nonTitleMatched_slot in [2, 3, 4]:
                return -1
            unPatternedTitle = re.sub(r"^\d{1,3}\s*[\.﹒．]\s*", "", title)
            
            if self.notTitleMatched(unPatternedTitle):
                return 6
            else:
                return possibleID
        
        if possibleID > -1:
            return possibleID

        if re.search(self.lowestHeaderPattern, title) and visattr in [AttrNorm.SECOND_LEVEL_TITLE.value,
                                                                     AttrNorm.FIRST_LEVEL_TITLE.value]:

            return self.lowestHeader
        elif visattr == AttrNorm.FIRST_LEVEL_TITLE.value:
            return self.nonMatchedTextHeader
        elif visattr == AttrNorm.SECOND_LEVEL_TITLE.value:
            return self.nonMatchedDocHeader

        return possibleID


    def nonfirstTitle(self):
        """
            判断是否是非首个标题，如果是则返回True，否则返回False
        该函数用于处理标题的逻辑，需要在使用前调用
        
        Args:
            无参数需求
        
        Returns:
            bool (bool): 如果是非首个标题，则返回True；否则返回False
        """
        # 判断是不否是第一个标题
        for preHeader in self.preHeader[::-1]:
            if preHeader["is_title"]:
                return True
        return False

    
    def getTitleBookIndex(self, title):
        """
            根据标题获取书籍索引，如果找不到则返回 -1
        
        Args:
            title (str): 书籍的标题，包含中文和数字，格式为 "第X章/篇/部分 XXXX" 或者 "上/下篇 XXXX"
        
        Returns:
            int: 返回标题中的数字或者对应的中文数字，如果找不到则返回 -1
        """
        # 获取到标题的 index，如果找不到，则返回 -1

        titleNumber = re.search(r"第([○-一二三四五六七八九十\d]*)(章|篇|部分).*", title)
        if titleNumber:
            titleNumber = titleNumber.group(1)

            if titleNumber.isdigit():
                titleNumber = int(titleNumber)
            elif titleNumber in self.ChineseNumber:
                titleNumber = self.ChineseNumber.index(titleNumber)
        else:
            titleNumber = re.search(r"(上|下)篇", title)
            if titleNumber:
                titleNumber = ["上", "下"].index(titleNumber.group(1))

        return titleNumber

    
    def getTitleOrder(self, title: str, titleRePos: int):
        """
        获取到标题在当前级别的顺序，例如（三）-> 3， 1.3 -> 3， 1.3.4 -> 4， 三 -> 3
        """
        if titleRePos in [0, 1, 2, 3, 5]:
            if titleRePos <= 2:
                titleOrder = self.getTitleBookIndex(title)
                if titleOrder:
                    if titleOrder in self.ChineseNumber:
                        titleOrder = self.ChineseNumber.index(titleOrder)
                    else:
                        titleOrder = None
            else:
                capital_order = re.search(r"\(?\s*([一二三四五六七八九十][一二三四五六七八九十]?[一二三四五六七八九十]?)\s*\)?", title)
                if capital_order:
                    titleOrder = capital_order.group(1)
                    if titleOrder in self.ChineseNumber:
                        titleOrder = self.ChineseNumber.index(titleOrder)
                    else:
                        titleOrder = None
                else:
                    titleOrder = None
                
            
            return titleOrder

        elif titleRePos in [6, 11, 12]:
            titleOrder = re.search(r"\(?\s*(\d+)\s*\)?", title).group(1)
            return int(titleOrder)

        else:
            return None


    def getHeaderContent(self, header_content):
        """
            获取头部内容，去除开始的非中文字符和“第”字符，如果存在则返回剩余部分。
        如果剩余部分包含中文或英文字母，则只保留中文字符。
        
        Args:
            header_content (str): 需要处理的头部内容。
        
        Returns:
            str: 处理后的头部内容，不包含开始的非中文字符和“第”字符，如果存在则返回剩余部分，如果剩余部分包含中文或英文字母，则只保留中文字符。
        """
        headerContent = re.sub(r"^[^\u4e00-\u9fff]{0,4}第((\d+)|([-一二三四五六七八九十][○-一二三四五六七八九十]?[○-一二三四五六七八九十]?))?章",
                                 "",
                                header_content).strip()
        searched = re.search(r"([\u4e00-\u9fffa-zA-Z]+)", headerContent)

        if searched:
            headerContent = re.sub(r"[^\u4e00-\u9fffa-zA-Z]", "", headerContent)

        return headerContent


    
    def ChapterTitleRefine(self, element: Element, structure: BaseStructure, eid: int):
        """
        一些书籍的章标题和 header 长的比较像，尤其是章的标题下方有一个横线，对于这样长相的标题，视觉模型经常会把它识别成header。
        这样的话会造成大标题的丢失，大标题的丢失会造成很多小标题挂载错误，这样影响召回。
        这个函数的作用是给定一个 element，来根据这个章标题的序号（比如第三章，那么这个序号就是2，第二章，那么需要就是1）以及章标题中的文本内容来对章标题进行修正。
        input：
            element: 章标题
            structure: 章标题所在的结构
        output:
            bool: element 是否是一个标题
        """


        
        #提取标题当中的序号
        CurTitleNumber = self.getTitleBookIndex(element.text)
        titleContent = self.getHeaderContent(element.text)
        
        #如果titleContent也就是传入的 element 在之前的章标题中出现过，那么返回 False，也就是不需要添加
        for addedHC in self.addedZhangHeader[-10: ]:

            if titleContent == addedHC["title"] and titleContent:
        
                return False
            
        # 如果同一页中已经出现了同一级的小于等于1的标题返回 False

        for preElement in structure[: eid][::-1]:
            if preElement.page_id == element.page_id and preElement.titleRePos == element.titleRePos:
                return False
            if preElement.page_id < element.page_id:
                break
        return True


    def mergeTitleFromHeader(self, header_content, nextTitle):
        """
            将下一个标题合并到当前标题中，如果下一个标题的页面ID与当前标题相同，且下一个标题不是非匹配文本或非匹配文档，则进行合并操作
        参数：
            header_content (dict): 包含当前标题信息的字典，格式为{"page_id": int, "header_content": str}
            nextTitle (dict): 包含下一个标题信息的字典，格式为{"page_id": int, "title": str, "titleRePos": int}
        返回值：
            dict: 返回更新后的字典，包含合并后的标题信息，格式为{"page_id": int, "header_content": str}
        """
        # 合并两个标题，如果下一个标题的级别大于当前标题，那么合并
        
        if header_content["page_id"] == nextTitle["page_id"]:


            if nextTitle.titleRePos == self.nonMatchedTextHeader or nextTitle.titleRePos == self.nonMatchedDocHeader: 
                header_content["header_content"] = header_content["header_content"].strip() + " " + \
                                                                                          nextTitle["title"].strip()
                return header_content
            
            elif "。" not in nextTitle and len(nextTitle) < 12 and \
                    (nextTitle.titleRePos == -1 or self.notTitleMatched(nextTitle["title"])):
                header_content["header_content"] = header_content["header_content"].strip() + " " + \
                                                                                          nextTitle["title"].strip()
                return header_content

            
    def judge_header_informative(self, element: Element) -> bool:
        """
        判断一个 header 是否是误识别的，如果把正文中的内容误识别了，那么把其informative 设置为 true，header 改为 doc_title
        input:
            element: 当前的 element
        output:
            bool: 是否是一个正文
        """
        finded = False
        headerContent = self.getHeaderContent(element.text)
        for addedHC in self.addedZhangHeader[-10: ]:
            if get_all_character(headerContent) == get_all_character(addedHC["title"]):
                # 如果在self.addedZhangHeader 中找到了，那么已经添加了
                finded = True
                break
        if not finded:
            element.informative = True
            #element.attr = AttrNorm.FIRST_LEVEL_TITLE.value
            self.addedZhangHeader.append({"title": headerContent, 
                                        "page_id": element.page_id, "title_ori": element.text})
            return True
        return False



    def isParentOf(self, parent, parentRePos, son, sonRePos):
        """
            判断子节点是否是父节点的父节点，只支持标题格式为1.1.1或者1.1.1.1等形式。
        如果父节点的rePos不为1，则认为是父节点的父节点。
        
        Args:
            parent (str): 父节点的字符串。
            parentRePos (int): 父节点在其父节点中的位置（从1开始）。
            son (str): 子节点的字符串。
            sonRePos (int): 子节点在其父节点中的位置（从1开始）。
        
        Returns:
            bool: 如果子节点是父节点的父节点，返回True；否则返回False。
        """
        # currently only support title like 1.1.1
        titleSignPattern = r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*(?!\s*[\.﹒．]\s*\d+)"
        SonSearched = re.search(titleSignPattern, son)
        ParentSearched = re.search(titleSignPattern, parent)
        if parentRePos == 1:
            return True
        if SonSearched and ParentSearched:
            SonSearchedString = SonSearched.group(0)
            ParentSearchedString = ParentSearched.group(0)
            SonSearchedDigits = re.split(r"[\.﹒．]", SonSearchedString)
            ParentSearchedDigits = re.split(r"[\.﹒．]", ParentSearchedString)
            for i, Pdigit in enumerate(ParentSearchedDigits):
                if Pdigit.strip() != SonSearchedDigits[i]:
                    return False
            return True

        
    def isBrotherOf(self, BigBrother, BigBrotherRePos, LittleBrother, LittleBrotherRePos):
        """
            判断两个兄弟节点是否为同一本书的不同版本，返回布尔值。
        大哥节点（BigBrother）和小弟节点（LittleBrother）都应该是已经排序好的字符串。
        如果两个节点都能匹配到标题签名，则认为他们是同一本书的不同版本。
        标题签名由数字、英文句号或者中文句号组成，最多包含5个部分，每个部分之间用英文句号或者中文句号隔开。
        例如：《围城》第2版，标题签名为：2.0
        参数（必要）列表：
            BigBrother (str) - 大哥节点（已排序好的字符串）
            BigBrotherRePos (int) - 大哥节点在原始文本中的起始位置
            LittleBrother (str) - 小弟节点（已排序好的字符串）
            LittleBrotherRePos (int) - 小弟节点在原始文本中的起始位置
        返回值（bool）：True代表两个节点是同一本书的不同版本，False代表不是。
        """

        titleSignPattern = r"^\d+(\s*[\.﹒．]\s*\d+){1,5}\s*(?!\s*[\.﹒．]\s*\d+)"
        BigBrotherSearched = re.search(titleSignPattern, BigBrother)
        LittleBrotherSearched = re.search(titleSignPattern, LittleBrother)
        if LittleBrotherSearched and BigBrotherSearched:
            BigBrotherSearchedString = BigBrotherSearched.group(0)
            LittleBrotherSearchedString = LittleBrotherSearched.group(0)
            BigBrotherSearchedDigits = re.split(r"[\.﹒．]", BigBrotherSearchedString)
            LittleBrotherSearchedDigits = re.split(r"[\.﹒．]", LittleBrotherSearchedString)
            if len(BigBrotherSearchedDigits) != len(LittleBrotherSearchedDigits):
                return False

            for i, Bdigit in enumerate(BigBrotherSearchedDigits):
                if i == len(BigBrotherSearchedDigits) - 1:

                    return True
                else:
                    if Bdigit.strip() == LittleBrotherSearchedDigits[i].strip():
                        continue
                    else:
                        return False


    def continuous(self, title):
        """
            判断一个标题是否连续出现在预处理后的列表中，并返回布尔值。
        参数（必需）：
            title (str) - 要查找的标题字符串。
        返回值（bool）- 如果该标题连续出现，则返回True；否则返回False。
        """
        traceId = self.preHeader.index(title)
        titleRePos = title.titleRePos
        for backward in self.preHeader[: traceId]:
            if backward["is_title"]:
                if backward["is_title"] == titleRePos:
                    return True
                else:
                    break
        for forward in self.preHeader[traceId + 1: ]:
            if forward["is_title"]:
                if forward.titleRePos == titleRePos:
                    return True    
                else:
                    break
        return False


    def justifyByPeerOrParant(self, element, structure, eid):
        """
        根据元素的 peer 或 parent 来进行对齐。
            如果元素的 peer 在结构中，则将元素的 level 设为 peer 的 level；
            如果元素的 parent 在结构中，则将元素的 level 设为 parent 的 level + 1；
            如果元素的 peer 和 parent 都在结构中，则将元素的 level 设为 peer 的 level + 1。
            如果元素的 peer 和 parent 都不在结构中，则将元素的 level 设为 1。
        
            Args:
                element (Element): 需要对齐的 Element 对象。
                structure (List[Element]): 包含所有 Element 对象的列表，用于查找 peer 和 parent。
                eid (int): 元素在结构中的索引。
        
            Returns:
                int: 元素的新 level。
        """

        def realJump(titlePrevious, titleBehind):
            if int(re.split(r"[\.﹒．]", titlePrevious.text)[0].strip()) < int(
                re.split(r"[\.﹒．]", titleBehind)[0].strip()):
                return True
            else:
                return False


        def justifyBetween(backtrackAgain, structure, eid):
            RePosToLevel = {}
            backtrackid = structure.index(backtrackAgain)
            lastheader = backtrackAgain

            for inter_element in structure[backtrackid + 1 : eid]:
                
                if inter_element.title_level != -1 and inter_element.informative:
                    if inter_element.title_level <= backtrackAgain.title_level:
                        if inter_element.titleRePos == lastheader.titleRePos:
                            inter_element.title_level = lastheader.title_level
                            RePosToLevel[inter_element.titleRePos] = lastheader.title_level

                        else:
                            if inter_element.titleRePos in RePosToLevel:

                                inter_element.title_level = RePosToLevel[inter_element.titleRePos] 
                            else:
                                inter_element.title_level = lastheader.title_level + 1
                                RePosToLevel[inter_element.titleRePos] = inter_element.title_level

                    lastheader = inter_element


        def justifyDigitTitleAccordingToDotDot(backtrackTitle, backtrackAgain, element, eid) -> int:
            currentTitle = element.text
            if backtrackAgain.titleRePos == 10:
                if realJump(backtrackAgain, currentTitle):
                    backtrackTitle.title_level = backtrackAgain.title_level - 4
                    return backtrackAgain.title_level - 3
                else:
                    justifyBetween(backtrackAgain,  structure, eid)
                    return backtrackAgain.title_level - 3
            elif backtrackAgain.titleRePos == 9:
                if realJump(backtrackAgain, currentTitle):
                    backtrackTitle.title_level = backtrackAgain.title_level - 3
                    return backtrackAgain.title_level - 2
                else:
                    justifyBetween(backtrackAgain,  structure, eid)
                    return backtrackAgain.title_level - 2
            elif backtrackAgain.titleRePos ==  8:
                if realJump(backtrackAgain, currentTitle):
                    backtrackTitle.title_level = backtrackAgain.title_level - 2
                    return backtrackAgain.title_level - 1
                else:
                    justifyBetween(backtrackAgain,  structure, eid)
                    return backtrackAgain.title_level - 1
            elif backtrackAgain.titleRePos ==  7:
                if realJump(backtrackAgain, currentTitle):
                    backtrackTitle.title_level = backtrackAgain.title_level - 1
                    return backtrackAgain.title_level
                else:
                    justifyBetween(backtrackAgain,  structure, eid)
                    return backtrackAgain.title_level
            elif backtrackAgain.titleRePos in [0, 1, 2]:
                return backtrackTitle.title_level + 1
            return 100000

        parent = self.ParentOf[element.titleRePos]
        son = self.sonOf[element.titleRePos]


        for bid, backtrackTitle in enumerate(structure[: eid][::-1]):
            if backtrackTitle.title_level == -1 or not backtrackTitle.informative:
                continue

            backtrackTitleString = backtrackTitle.text
 
            if backtrackTitle.titleRePos in parent:  
                # 1.1 2.1 3.2 等这些的 parent 是 1，或者第一章、第一节
                if element.titleRePos == 7 and backtrackTitle.titleRePos in [0, 1, 2, 6]: #找到其父标题
                    # 如果是单个数字

                    if backtrackTitle.titleRePos == 6:# and not self.continuous(backtrackTitle):

                        # 如果这个单个数字与 当前标题的第一个数字相同
                        # if re.search(r"^\d+", backtrackTitle["title"]).group(0) == re.split(r"[\.﹒．]", title)[0].strip():
                        #     # 当个小数字不可置信，继续往前回溯

                        if self.titleLevelStart(element.text) and backtrackTitle.text.lstrip()[0] == "1":
                            self.SuccessorOf[6].update([7, 8, 9, 10])
                            self.AncestorOf[7].update([6])
                            self.AncestorOf[8].update([6])
                            self.AncestorOf[9].update([6])
                            self.AncestorOf[10].update([6])
                            return backtrackTitle.title_level + 1

                        else:

                            backtrack_index = structure.index(backtrackTitle)
                            for backtrackAgain in structure[: backtrack_index + 1][::-1]:

                                if backtrackAgain.title_level == -1 or not backtrackAgain.informative:
                                    continue

                                header_level = justifyDigitTitleAccordingToDotDot(
                                    backtrackTitle, backtrackAgain, element, eid)

                                if header_level != 100000:
                                    return header_level 
                        return backtrackTitle.title_level + 1 #如果没有找到，上一个层级 + 1


                    elif backtrackTitle.titleRePos in [0, 1, 2]:
                        return backtrackTitle.title_level + 1


                
                elif self.isParentOf(backtrackTitle.text, backtrackTitle.titleRePos, element.text, element.titleRePos):

                    if bid == 0:
                        return backtrackTitle.title_level + 1
                    else:
                        justifyBetween(backtrackTitle, structure, eid)
                    return backtrackTitle.title_level + 1
                else:
    
                    continue
            elif backtrackTitle.titleRePos in son:

                justifyBetween(backtrackTitle, structure, eid)
                return backtrackTitle.title_level - (backtrackTitle.titleRePos -element.titleRePos)
             # by peer
            elif backtrackTitle.titleRePos == element.titleRePos:

                if self.isBrotherOf(backtrackTitle.text, backtrackTitle.titleRePos, element.text, element.titleRePos):

                    if bid == 0:
                        return backtrackTitle.title_level
                    else:

                        justifyBetween(backtrackTitle, structure, eid)
                    return backtrackTitle.title_level

                else:   
                    continue
            elif backtrackTitle.titleRePos in self.AncestorOf[element.titleRePos]:

                return backtrackTitle.titleRePos + 1


    def predict(self, structure: BaseStructure, knowledge_type: Union[KnowledgeType, None] = KnowledgeType.BOOK) -> BaseStructure:
        """
        预测标题的层级，输入一个 structure 对象，对structure 中所有的 element 赋予层级，如果不是标题，那么就赋予-1
        """
        self.reset()
        # 对于book 来说，经常标题层级是 第一章 > 1.1 > 1.1.1 > 一，> 1, 如果不是 book 的话，就很少出现这种情况
        if knowledge_type != KnowledgeType.BOOK.value: # and knowledge_type != KnowledgeType.DRUG_INSTRUCTION.value:
            
            self.SuccessorOf[3].update([7, 8, 9, 10])
            self.SuccessorOf[6].update([7, 8, 9, 10])
            self.AncestorOf[7].update([3, 6])
            self.AncestorOf[8].update([3, 6])

            self.AncestorOf[9].update([3, 6])
            self.AncestorOf[10].update([3, 6])
        
        if knowledge_type == KnowledgeType.DRUG_INSTRUCTION.value: # 药品说明书,最大一级标题是 doc_title，然后是【】

            self.undefineP = []
            self.AncestorOf[4] = [self.nonMatchedDocHeader]

            self.SuccessorOf[4] = set([0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                      self.nonMatchedTextHeader, self.lowestHeader])
            self.AncestorOf[0].update([4])
            self.AncestorOf[1].update([4])
            self.AncestorOf[2].update([4])
            self.AncestorOf[3].update([4])
            self.AncestorOf[5].update([4])
            self.AncestorOf[6].update([4])
            self.AncestorOf[7].update([4])
            self.AncestorOf[8].update([4])
            self.AncestorOf[9].update([4])
            self.AncestorOf[10].update([4])
            self.AncestorOf[11].update([4])
            self.AncestorOf[12].update([4])
            self.AncestorOf[13].update([4])
            self.AncestorOf[self.lowestHeader].update([4])
            self.AncestorOf[self.nonMatchedTextHeader].update([4])

        if knowledge_type ==  KnowledgeType.BOOK.value:
            self.title_re_list[4] = self.book_bracket_pattern


        for eid, element in enumerate(structure):

            element.titleRePos = self.get_title_slot(element)

            merged = self.merge_title(element, eid, structure)

            if merged: # 如果合并了，那么就不需要往下走层级识别
                self.addedZhangHeader.append({"title": self.getHeaderContent(
                    structure[eid - 1].text), "page_id": element.page_id})
                continue
        
            # 如果判断不是标题，则直接返回
            if element.titleRePos == - \
                1 and not self.isHeader(Title=element.text, attr=element.attr, page_id=element.page_id):
                continue

            if element.titleRePos == -1:
                continue

            # 如果是 header，那么看在self.addedZhangHeader 中是否有这个标题，如果没有，那么就把这个header 的informative 设置为True
            if element.titleRePos in [0, 1]:

                if element.attr == AttrNorm.HEADER.value:
                    usable = self.judge_header_informative(element)

                    if not usable:
                        continue
                else:
                    isTitle = self.ChapterTitleRefine(element, structure, eid)
                    if not isTitle:
                        element.informative = False
                        continue
                    else:
                        self.addedZhangHeader.append({"title": self.getHeaderContent(
                            element.text), "page_id":element.page_id, "title_ori":element.text})

            if not element.informative:
                continue

            if self.not_encounter_title_before: #如果是这本书遇到的第一个标题，那么将其的层级赋值为0
                element.title_level = 0
                self.not_encounter_title_before = False
                continue
            
            else: #如果不是第一级标题，那么根据上一级标题以及存储下来的标题来判断标题的层级
                # 获取到必定能成为当前标题的祖先标题以及继承标题

                definedAncestor = self.AncestorOf[element.titleRePos]
                definedSuccessor = self.SuccessorOf[element.titleRePos]

                lastHeader = self.getLastHeader(element, structure, eid)



                last_title_level = lastHeader.title_level  #上一个标题中的层级
                last_titleRePos = lastHeader.titleRePos  #标题正则表达式list中的index
                lastTitleString = lastHeader.text

                if lastHeader.titleRePos == 4 and knowledge_type == KnowledgeType.DRUG_INSTRUCTION.value:
                    self.AncestorOf[self.nonMatchedDocHeader].update([4])
                    self.AncestorOf[4] = set([])
                    self.SuccessorOf[4].update([self.nonMatchedDocHeader])


                if last_titleRePos == element.titleRePos: #如果上一个标题和当前标题的 pattern 相同
                    element.title_level = last_title_level
                    continue
                
                # 如果前面一个标题的 pattern 是当前标题的祖先，那么当前标题的层级就等于上一级标题的层级 + 1
                elif last_titleRePos in definedAncestor:

                    headerLevel = last_title_level + 1
                    element.title_level = headerLevel

                    continue
                # 如果上一级标题是当前标题的继承者，需要重新判断标题的层级
                elif last_titleRePos in definedSuccessor or element.titleRePos in self.undefineP:

                    if structure[eid - 1].title_level != -1 and (self.whereTitleMatched(
                        structure[eid - 1].text) or structure[eid - 1].titleRePos in self.goBack) and element.titleRePos in self.undefineP:

                        element.title_level = structure[eid - 1].title_level + 1
                        continue
                    last_header_index = structure.index(lastHeader)
                    backPreHeader = structure[:last_header_index][::-1] #回溯到以前的标题


                    # 从存储的标题中寻找到当前标题的祖先以及具有相同 pattern 的标题， 
                    ## 如果找到祖先标题，则当前标题的层级就等于祖先标题的层级 + 1， 
                    ## 如果找到具有相同 pattern 的标题，则当前标题的层级就等于其层级
                    ## 并且记录比当前层级小的最大一级别标题，如果前两者都没有找到，则将其层级小的最大一级别标题的层级 + 1 作为当前标题的层级
                    uppermost = last_title_level
                    for id, preTitle in enumerate(backPreHeader):

                        if preTitle.title_level == -1 or not preTitle.informative:
                            continue

                        Pre_title_level = preTitle.title_level  #上一个标题中的层级
                        Pre_titleRePos = preTitle.titleRePos  #标题正则表达式list中的index
                        # 注意，title_level 越大，越接近根节点，title_level 越小，越远离根节点
                        if Pre_titleRePos in definedSuccessor:
                            if Pre_title_level < uppermost and Pre_title_level != -1:
                                uppermost = Pre_title_level

                        elif Pre_titleRePos in definedAncestor:  #如果找到其祖先标题

                            if element.titleRePos in self.undefineP:
                                headerLevel = last_title_level + 1
                            else:
                                headerLevel = Pre_title_level + 1
                            
                            element.title_level = headerLevel

                            break

                        elif element.titleRePos == Pre_titleRePos: #找到相同的title level

                            pre_title_order = self.getTitleOrder(preTitle.text, Pre_titleRePos)
                            cur_title_order = self.getTitleOrder(element.text, element.titleRePos)

                            if pre_title_order and cur_title_order and pre_title_order + 1 == cur_title_order:
                                pre_index = structure.index(preTitle)
        
                                for ith, interTitle in enumerate(structure[pre_index + 1: eid]):
                                    if ith == 0:
                                        move_level = 1
                                    else:
                                        move_level = max(interTitle.title_level - \
                                                         structure[pre_index + 1].title_level + 1, 1)
                                    if interTitle.title_level <= Pre_title_level and interTitle.title_level != -1 and interTitle.informative:
                                        interTitle.title_level = Pre_title_level + move_level

                            headerLevel = Pre_title_level

                            element.title_level = preTitle.title_level

                            break

                    # 如果一直没有找到与其相同的 pattern 或者其祖先标题，找到以前比其层级小的最大一级标题，并将其层级赋值给当前层级
                    #if titleRePos in self.undefineP:
                    if element.title_level != -1:
                        continue

                    if uppermost != last_title_level:

                        if element.titleRePos in self.undefineP:
                            headerLevel = uppermost + 1
                        else:
                            headerLevel = uppermost 
                        element.title_level = headerLevel
                        continue
                    else:  # 如果没有比其层级小的最大一级标题，则出现跑出异样，因为进来的条件是上一层级是这一层级的继承 

                        #raise  Exception(f"没有找到比其层级小的最大一级标题, {title}")
                        headerLevel = last_title_level
                        element.title_level = headerLevel
                        continue
                # 如果当前的标题是【】

                elif element.titleRePos in self.goBack: # 这里是没有任何标记的doc_title, 或者是 text_title , 原本只能靠语义来区分
                    # 如果其紧邻着的上一级instance 是标题，那么就直接为上一个标题的子集

                    if structure[eid - 1].title_level != -1 and \
                        (self.whereTitleMatched(structure[eid - 1].text) or structure[eid - 1].titleRePos in self.goBack ):

                        headerLevel = structure[eid - 1].title_level + 1
                        element.title_level = headerLevel

                    backPreHeader = structure[: eid][::-1] #回溯到以前的标题

                    # 从存储的标题中寻找到当前标题的祖先以及具有相同 pattern 的标题， 
                    ## 如果找到祖先标题，则当前标题的层级就等于祖先标题的层级 + 1， 
                    ## 如果找到具有相同 pattern 的标题，则当前标题的层级就等于其层级
                    ## 并且记录比当前层级小的最大一级别标题，如果前两者都没有找到，则将其层级小的最大一级别标题的层级 + 1 作为当前标题的层级
                    uppermost = 100
                    for bid, preTitle in enumerate(backPreHeader):
                        if preTitle.title_level == -1 or not preTitle.informative:
                            continue

                        Pre_title_level = preTitle.title_level  #上一个标题中的层级
                        Pre_titleRePos = preTitle.titleRePos  #标题正则表达式list中的index

                        # 注意，title_level 越大，越接近根节点，title_level 越小，越远离根节点
                        if Pre_titleRePos in definedSuccessor:
                            if Pre_title_level < uppermost and Pre_title_level != -1:
                                uppermost = Pre_title_level

                        elif preTitle.meta_name in self.gobackStopMetaSign:

                            headerLevel = last_title_level + 1
                            element.title_level = headerLevel
                            break

                        elif Pre_titleRePos in definedAncestor:  #如果找到其祖先标题
                            if element.titleRePos in self.goBack:
                                headerLevel = last_title_level + 1

                            else:

                                headerLevel = Pre_title_level + 1
                            element.title_level = headerLevel
                            break

                        elif Pre_titleRePos in self.goBack: #找到相同的title level

                            headerLevel = Pre_title_level 
                            element.title_level = headerLevel
                            break
                        elif self.titleLevelStart(lastHeader.text) and element.titleRePos in self.goBack:
                            headerLevel = last_title_level + 1
                            element.title_level = headerLevel
                            break

                    if element.title_level != -1:
                        continue
                    # 如果一直没有找到与其相同的 pattern 或者其祖先标题，找到以前比其层级小的最大一级标题，并将其层级赋值给当前层级
                    #if titleRePos in self.undefineP:

                    if uppermost != 100:
                        if element.titleRePos in self.undefineP:
                            headerLevel = uppermost + 1
                        else:
                            headerLevel = uppermost 
                        element.title_level = headerLevel
                        continue
                    else:  # 如果没有比其层级小的最大一级标题，则出现跑出异样，因为进来的条件是上一层级是这一层级的继承 

                        #raise  Exception(f"没有找到比其层级小的最大一级标题, {title}")
                        headerLevel = last_title_level
                        element.title_level = headerLevel
                        continue

                elif last_titleRePos in self.undefineP or last_titleRePos in self.goBack: # 上一层级是 【x】

                    # 如果当前层级是1，第一章、第一节这些
                    if self.titleLevelStart(element.text):
                        # 不能直接加一，得往回寻找
                        # 如果【x】的上一级是和当前层级一样的pattern，那么【x】是其前一层级的就是比其上一层级大一级
                        # （三）xx
                        #  【x】
                        # (一)xx
                        # -------------
                        # ##（三）xx
                        # #【x】
                        # # (一)xx

                        # 找到前一层级的前一层次
  
                        last_index = structure.index(lastHeader)
                        lastPreHeaders = structure[: last_index]

                        uppermost = 100
                        for preHeader in lastPreHeaders[::-1]:
                            # 往回回溯
                            if not preHeader.informative or preHeader.title_level == -1:
                                continue
                            preHeader_titleRePos = preHeader.titleRePos
                            preHeader_title_level = preHeader.title_level
                            #如果找到和当前标题 pattern 相同的 pattern
                            if preHeader_titleRePos == element.titleRePos:

                                lastHeader.title_level = preHeader_title_level - 1
                                headerLevel = preHeader_title_level
                                element.title_level = headerLevel
                                break

                            elif preHeader_titleRePos in definedAncestor:

                                lastHeader.title_level = preHeader_title_level + 1
                                headerLevel = preHeader_title_level + 2
                                element.title_level = headerLevel

                                break

                            elif preHeader_titleRePos in self.undefineP and last_titleRePos in self.undefineP:

                                element.title_level = lastHeader.title_level + 1
                                # if preHeader_title_level < uppermost and preHeader_title_level != -1:
                                #     uppermost = preHeader_title_level
                                break
                        
                        if element.title_level != -1:
                            continue

                        if uppermost != 100:
                            if element.titleRePos in self.undefineP:
                                headerLevel = uppermost + 1
                            else:
                                headerLevel = uppermost 
                            element.title_level = headerLevel
                            continue
                        else:
                            #raise  Exception(f"没有找到比其层级小的最大一级标题, {title}")
                            headerLevel = last_title_level + 1
                            element.title_level = headerLevel
                            continue
                    # 如果不是第一章第一节1 、这些
                    else:

                        backPreHeader = structure[: eid][::-1] #回溯到以前的标题
                        for id, preTitle in enumerate(backPreHeader):

                            if preTitle.title_level == -1 or not preTitle.informative:
                                continue
                            pre_title_string = preTitle.text
                            Pre_title_level = preTitle.title_level  #上一个标题中的层级
                            Pre_titleRePos = preTitle.titleRePos  #标题正则表达式list中的index

                            if element.titleRePos == Pre_titleRePos: #找到相同的

                                pre_title_order = self.getTitleOrder(pre_title_string, Pre_titleRePos)

                                cur_title_order = self.getTitleOrder(element.text, element.titleRePos)

                                if pre_title_order and cur_title_order and pre_title_order + 1 == cur_title_order:
                                    lastHeader.title_level = Pre_title_level + 1

                                headerLevel = Pre_title_level
                                element.title_level = headerLevel

                                break

                            if Pre_titleRePos in definedAncestor:  #如果找到其祖先标题

                                headerLevel = Pre_title_level + 1
                                element.title_level = headerLevel
                                break

                        
                
                elif element.titleRePos in self.ParallelUniverse:

                    headerLevel = self.justifyByPeerOrParant(element, structure, eid)
                    if headerLevel is not None:
                        element.title_level = headerLevel
                        continue
                    else:
                        if self.titleLevelStart(
                            element.text) and last_titleRePos == 6 and self.titleLevelStart(lastHeader.text):
                            element.title_level = lastHeader.title_level + 1
                            continue 

                elif last_titleRePos in self.ParallelUniverse:

                    if self.titleLevelStart(element.text):

                        if 6 in self.AncestorOf[last_titleRePos]: 
                            if 6 in self.SuccessorOf[element.titleRePos]:
                                self.SuccessorOf[element.titleRePos].remove(6)
                            if element.titleRePos in self.AncestorOf[6]:
                                self.AncestorOf[6].remove(element.titleRePos)

                            self.AncestorOf[element.titleRePos].update([6, 7, 8, 9])
                            self.SuccessorOf[6].add(element.titleRePos)



                        headerLevel = last_title_level + 1
                        element.title_level = headerLevel
                        continue
                    else:
                        backPreHeader = structure[: eid][::-1] #回溯到以前的标题
                        for id, preTitle in enumerate(backPreHeader):
                            # if not preTitle["is_title"]:
                            #     continue
                            if preTitle.title_level == -1 or not preTitle.informative:
                                continue
                            Pre_title_level = preTitle.title_level  #上一个标题中的层级
                            Pre_titleRePos = preTitle.titleRePos  #标题正则表达式list中的index


                            if element.titleRePos == Pre_titleRePos: #找到相同的

                                headerLevel = Pre_title_level
                                element.title_level = headerLevel
                                break

                            if Pre_titleRePos in definedAncestor:  #如果找到其祖先标题

                                headerLevel = Pre_title_level + 1
                                element.title_level = headerLevel
                                break

                        continue

            # 最后的预防 bug 机制
            if self.not_encounter_title_before:

                preTitle = self.getLastHeader(element, structure, eid)
                
                Pre_title_level = preTitle.title_level
                Pre_titleRePos = preTitle.titleRePos

                headerLevel = Pre_title_level + 1
            else: 
                headerLevel = 1
            if element.title_level == -1:
                element.title_level = headerLevel
        self.postProcess(structure)
        return structure
    

    def whereTitleMatched(self, title):
        """
            判断标题是否匹配，如果匹配则返回True，否则返回False。
        该函数会遍历所有的正则表达式，如果任意一个正则表达式与标题匹配，则返回True。
        
        Args:
            title (str): 需要匹配的标题字符串。
        
        Returns:
            bool: 如果匹配则返回True，否则返回False。
        """
        for id, title_re in enumerate(self.whether_title_re_list):
            title = title.strip()
            if re.search(title_re, title):
                return True
        return False


    def notTitleMatched(self, title):
        """
            判断标题是否匹配不包含的列表，如果匹配则返回对应id+1，否则返回False
        参数:
            - title (str) - 需要匹配的标题字符串
        返回值:
            - bool/int - 如果匹配到了，返回对应id+1；如果没有匹配到，返回False
        """
        for id, title_re in enumerate(self.notTitle):
            title = title.strip()
            if re.search(title_re, title):
                return id + 1
        
        
        return False


    def isHeader(self, Title: str, attr: str, page_id: int) -> bool:
        """
        在这里只限制两个，第一个是
        """

        def notTitleMatched(title):
            for id, title_re in enumerate(self.notTitle):
                title = title.strip()
                if re.search(title_re, title):
                    return True
            return False
        # 只有数字，没有中英文
        if not re.search(r"[\u4e00-\u9fffa-zA-Z]", Title):
            return False

        if notTitleMatched(Title) and not attr in [AttrNorm.SECOND_LEVEL_TITLE.value, AttrNorm.FIRST_LEVEL_TITLE.value]:
            return False


        if attr == AttrNorm.SECOND_LEVEL_TITLE.value or attr == AttrNorm.FIRST_LEVEL_TITLE.value:
            
            if not re.search(r"^(表|图)[\dⅠⅡⅢⅣ]+.*", Title):
                return True
            return False

        return True


    def postProcess(self, structure: BaseStructure):
        """
        注意这里不改变标题的层级
        在这里对前面所有的标题进行后处理操作
        1，去除一些乱入的标题
          1）如果一序列连续的标题，这一系列连续的标题内没有比其更小一级的标题，则把这些标题层级变为0
        2, 对于行内标题下面还有更细小一级的标题，提取行内的标题
          例如：
          ## (三) 诊断 糖尿病的诊断分为很多类型 ......
            ### 1,a 型 看见的垃圾
            ### 2,b 型 看不见的垃圾
          改为：
          ## （三) 诊断
             糖尿病的诊断分为很多类型 ......
            1,a 型 看见的垃圾......
            2,b 型 看不见的垃圾......
        """
        # 将参考文献、思考题等标题去掉

        lastlevelRePos = 100
        lastRePos = 100

        for header in structure:
            if header.titleRePos in [6, 7, 11, 13] and (
                lastlevelRePos == self.lowestHeader or lastRePos == self.lowestHeader) and header.attr == AttrNorm.PARA.value:


                header.title_level = -1
            if header.titleRePos != -1:
                if lastRePos != header.titleRePos and lastRePos != 13:

                    lastlevelRePos = lastRePos
                lastRePos = header.titleRePos

        # 对所有的节点区分是否是叶子节点

        for index in range(1, len(structure) - 1):

            left = None
            right = None
            for backword in structure[: index][::-1]:
                if backword.title_level != -1 and backword.title_level != structure[index].title_level:
                    left = backword
                    break
            for forward in structure[index + 1: ]:
                if forward.title_level != -1 and forward.title_level != structure[index].title_level:
                    right = forward
                    break
            if left is None or right is None:
                structure[index].leafNode = False
                continue

            if structure[index].title_level >= right.title_level \
                    and structure[index].title_level >= left.title_level\
                       and structure[index].titleRePos in [6, 11, 12, 13]\
                          and left.title_level != 0\
                                and right.title_level != 0:

                structure[index].leafNode = True
            else:
                structure[index].leafNode = False
        
        # 所有的非叶子节点提取其标题，如果有行内标题标识，则直接提取标题，如果没有则提取前12个字，并打上『...』
        for index, header in enumerate(structure):
            #非叶子节点
            if not header.leafNode and header.title_level != -1 \
                and count_ch_characters(header.text) > 30 \
                    and re.search(r'[\u4e00-\u9fff]', header.text):
                    
                header = self.header_extracter.extract(header)
            # 叶子节点
            if header.leafNode and count_ch_characters(header.text) > 50:
                header.title_level = -1
            
            if header.leafNode and structure[min(len(structure) - 1, index + 1)].title_level == header.title_level:

                header.title_level = -1

            if header.leafNode and not self.whereTitleMatched(header.text):

                header.title_level = -1
            

  
if __name__ == "__main__":
    dh = DynamicTitleParser()
    from src.parse.pdf.pdf_structure import PDFStructure
    pdf_structure = PDFStructure()
    el1 = Element(text="第一章", attr=AttrNorm.FIRST_LEVEL_TITLE, para_id=0, page_id=0, catelog_page=False)
    el2 = Element(text="天大", attr=AttrNorm.PARA, para_id=1, page_id=0, catelog_page=False)
    el3 = Element(text="第三章 嘀嗒", attr=AttrNorm.HEADER, para_id=2, page_id=2, catelog_page=False)
    el4 = Element(text="(一)这是一个啥也不 u嗒", attr=AttrNorm.PARA, para_id=3, page_id=3, catelog_page=False)
    el5 = Element(text="1.嘀嗒", attr=AttrNorm.SECOND_LEVEL_TITLE, para_id=3, page_id=3, catelog_page=False)
    pdf_structure.add(el1)
    pdf_structure.add(el2)
    pdf_structure.add(el3)
    pdf_structure.add(el4)
    pdf_structure.add(el5)
    
    dh.predict(pdf_structure)
    for el in pdf_structure:
        print(el)
    print(pdf_structure.index(el5))
    # print(pdf_structure[3])
    #dh.predict(pdf_structure)
