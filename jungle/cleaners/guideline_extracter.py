#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
extract mete data from guideline
@author: 1329239119@qq.com

usage:
    
"""
from LAC import LAC
import nltk
from nltk import word_tokenize
from nltk import pos_tag
from src.jungle.structure.structure import BaseStructure
from src.jungle.schema.entity import GuidelineEntities
from src.jungle.schema.entity import Language
from src.jungle.title.utils import contain_chinese
import re
import spacy

nltk.data.path.append('src/checkpoints/dict/nltk_data')


class GuidelineExtracter(object):
    """
    extractor meta data from guideline
    """
    def __init__(self):
        """
            初始化函数，用于初始化类属性和方法。
        初始化了一些正则表达式模式，以及LAC分词器、spaCy NLP处理工具等。
        
        Args:
            None.
        
        Returns:
            None.
        
        Raises:
            None.
        """
        self.CHINESE_ABSTRACT_PATTERN = re.compile(r"^(#*\s*[【\[]\**[摘提]要[】\]]\s*\**|摘要：?|摘要目的：?)")
        self.ENGLISH_ABSTRACT_PATTERN = re.compile(
            r"^[【\[]?\**\s*(Abstract|ABSTRACT)\s*(OBJECTIVE|Objective)?\s*\**[】\]:：；]?") 
        self.CHINESE_KEYWORD_PATTERN = re.compile((r"^(#*\s*[【\[](关\s?键\s?词|主\s?题\s?词|)[】"
                                                    r"\]]\s*|(关\s?键\s?词|主\s?题\s?词)：?)"))
        self.ENGLISH_KEYWORD_PATTERN = re.compile(
            r"^#*[【\[]?\s*\**(Key\s*words|KEYWORDS|Subject\s*words)\**\s*[】\]:：；]?")
        self.CHINESE_AUTHOR_PATTERN = re.compile(r"^[【\[]?(通讯作者|通信作者|作者简介|E-mail|Email|通讯作者邮箱)[\:：；\]】].*")
        self.ENGLISH_AUTHOR_PATTERN = re.compile(r"^(\**Corresponding\s*authors\**?:|Email:)")
        self.PROJECT_FUND_PATTERN = re.compile((r"^[【\[]?\s*(项目资助|项目基金|基金项目|"
                                                r"Project\s*funding|Fund\s*program)\s*[】\]:：；]?"))
        self.DOI_PATTERN = re.compile(
            r"^#*\s*((DOI|doi|Doi)[:;；：]|[【\[][Dd][Oo][Ii][】\]]|[【\[]中国分类号[\]】]|[【\[]文献标识码[】\]]).+")
        self.WEBPAGE_PATTERN = re.compile(
                                            (r"^(https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,}(?:\/[\-a-z\d%_.~+]*)*"
                                             r"(?:\?[;&a-z\d%_.~+=-]*)?(?:\#[\-a-z\d_]*)?$)|^[a-zA-Z0-9._%+-]"
                                             r"+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                                        ))
        self.REFERENCE_PATTERN = re.compile(r"^\[\s*\d+\s*].+")
        self.USENESS_PATTERN = re.compile(
            r"\s*\·?\s*标?准?\s*\·?\s*指?南?\·?\s*共?识?\·*?\s*综?述?\·\s*\·?译?文?\·?\·?临?床?研?究?\·?")
        self.lac_seg = LAC(mode='seg')
        self.lac_pos = LAC(mode='lac')
        self.nlp = spacy.load('en_core_web_sm')
        self.organition = None
        self.chinese_abstract = None
        self.english_abstract = None
        self.chinese_keyword = None
        self.english_keyword = None
        self.chinese_title = None
        self.english_title = None
        self.chinese_author = None
        self.english_author = None
        self.doi = None
        self.project_funding = None


    def is_chinese_abstract(self, text: str) -> bool:
        """
        return True if text is abstract of paper
        """
        if self.chinese_abstract:
            return False
        
        if self.CHINESE_ABSTRACT_PATTERN.search(text):
            return True
        return False

    
    def is_webset(self, text: str) -> bool:
        """
        return True if text is webset of paper
        """
        if self.WEBPAGE_PATTERN.search(text):
            return True
        return False


    def is_english_abstract(self, text: str) -> bool:
        """
        return True if text is abstract of paper
        """
        if self.english_abstract:
            return False
        if self.ENGLISH_ABSTRACT_PATTERN.search(text):
            return True
        return False


    def is_chinese_keyword(self, text: str) -> bool:
        """
        return True if text is keyword of paper
        """
        if self.chinese_keyword:
            return False
        if self.CHINESE_KEYWORD_PATTERN.search(text):
            return True
        return False


    def is_english_keyword(self, text: str) -> bool:
        """
        return True if text is keyword of paper
        """

        if self.ENGLISH_KEYWORD_PATTERN.search(text):
            return True
        return False


    def is_english_title(self, text: str, visattr="text") -> bool:
        """
        return True if text is title of paper, if a title is a english title
        """

        if self.english_title:
            return False
        
        if contain_chinese(text): #包含中文字符
            return False

        if self.REFERENCE_PATTERN.search(text):
            return False

        if self.WEBPAGE_PATTERN.search(text):
            return False

        tokens = word_tokenize(text)
        if len(tokens) > 5 and len(tokens) < 100:
            return True
        return False


    def is_project_funding(self, text: str) -> bool:
        """
        return True if text is project funding of paper
        """

        if self.PROJECT_FUND_PATTERN.search(text):
            return True
        return False


    def is_chinese_author(self, text: str) -> bool:
        """
        return True if text is author of paper
        """
        number_person_token = 0
        number_org_token = 0
        number_noun_token = 0
        number_token = 0.0001
        doc = self.lac_pos.run(text)

        for tag in doc[1]:
            if tag in ["PER", "ORG"]:
                number_person_token += 1
            
            if tag in ["n", "nz"]:
                number_noun_token += 1

            if not tag in ["w", "m"]:
                number_token += 1

        if number_person_token / number_token > 0.6:

            return True

        if self.CHINESE_AUTHOR_PATTERN.search(text):
            return True
        return False


    def is_english_author(self, text):
        """
        return True if text is author of paper
        """
        if contain_chinese(text): #包含中文字符
            return False

        number_person_token = 0
        number_token = 0.0001
        doc = self.nlp(text)
        for token in doc:
            if token.ent_type_ in ["PERSON", "ORG"]:
                number_person_token += 1

            if token.pos_ != "PUNCT":
                number_token += 1
        if number_person_token / number_token > 0.6:
            return True

        if self.ENGLISH_AUTHOR_PATTERN.search(text):
            return True
        
        return False


    def is_doi(self, text):
        """
        is possible doi of paper
        input:
            text: str, the text need to be judged
        output:
            True: is possible doi of paper
            False: is not possible doi of paper
        """
        if self.DOI_PATTERN.search(text):
            return True
        else:
            return False


    def is_useless(self, text):
        """
        return True if text is useness of paper
        """
        if self.USENESS_PATTERN.search(text):
            return True
        return False


    def to_dict(self):
        """
        return dict of text type
        """
        return {
            GuidelineEntities.CHINESE_ABSTRACT.value: self.chinese_abstract,
            GuidelineEntities.ENGLISH_ABSTRACT.value: self.english_abstract,
            GuidelineEntities.CHINESE_KEYWORD.value: self.chinese_keyword,
            GuidelineEntities.ENGLISH_KEYWORD.value: self.english_keyword,
            GuidelineEntities.ENGLISH_TITLE.value: self.english_title,
            GuidelineEntities.CHINESE_AUTHOR.value: self.chinese_author,
            GuidelineEntities.ENGLISH_AUTHOR.value: self.english_author,
            GuidelineEntities.DOI.value: self.doi,
            GuidelineEntities.PROJECT_FUNDING.value: self.project_funding,
            }


    def funnel(self, text: str, page_id: int, lang: Language=Language.CHINESE.value):
        """
        funnel all text to one type of text
        """
        if page_id > 1: #meta data normally in page 0 and 1
            return {"is_meta": False, "meta_name": ""}
        if self.is_chinese_abstract(text):
            self.chinese_abstract = text
            return {"is_meta": True, "meta_name": GuidelineEntities.CHINESE_ABSTRACT.value}
        elif self.is_english_abstract(text):
            self.english_abstract = text
            return {"is_meta": True, "meta_name": GuidelineEntities.ENGLISH_ABSTRACT.value}
        elif self.is_chinese_keyword(text):
            self.chinese_keyword = text
            return {"is_meta": True, "meta_name": GuidelineEntities.CHINESE_KEYWORD.value}
        elif self.is_english_keyword(text):
            self.english_keyword = text
            return {"is_meta": True, "meta_name": GuidelineEntities.ENGLISH_KEYWORD.value}
            
        elif self.is_doi(text):
            self.doi = text
            return {"is_meta": True, "meta_name": GuidelineEntities.DOI.value}
         #有一些识别乱码，所以中文摘要和关键词也是一个判定要素
        elif self.is_english_title(text) and \
                (lang == Language.CHINESE.value or self.chinese_abstract or self.chinese_keyword): 

            self.english_title = text
            return {"is_meta": True, "meta_name": GuidelineEntities.ENGLISH_TITLE.value}
        elif self.is_chinese_author(text):
            self.chinese_author = text if not self.chinese_author else self.chinese_author + ";" + text
            return {"is_meta": True, "meta_name": GuidelineEntities.CHINESE_AUTHOR.value}
        elif self.is_english_author(text):
            self.english_author = text if not self.english_author else self.english_author + ";" + text
            return {"is_meta": True, "meta_name": GuidelineEntities.ENGLISH_AUTHOR.value}

        elif self.is_project_funding(text):
            self.project_funding = text if not self.project_funding else self.project_funding + ";" + text
            return {"is_meta": True, "meta_name": GuidelineEntities.PROJECT_FUNDING.value}

        else:
            return {"is_meta": False, "meta_name": ""}


    def extract(self, structure: BaseStructure):
        """
        extract meta data from structure
        """
        for element in structure:
            meta_json = self.funnel(element.text, element.page_id)
            if meta_json["is_meta"]:
                element.meta_name = meta_json["meta_name"]


    def __str__(self):
        """
            返回字符串形式的对象名称，默认为对象名称。
        可以重写此方法来定义自己的字符串表示形式。
        
        Returns:
            str -- 对象名称，默认为对象名称。
        """
        return self.name
