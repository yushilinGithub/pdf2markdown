#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
spacy英文分词

安装依赖：
    spacy
    ./lib/en_core_web_sm-3.6.0-py3-none-any.whl

参考教程：
    其他模型参考: https://spacy.io/usage/models
    https://spacy.io/usage/linguistic-features#pos-tagging
    https://spacy.io/usage/rule-based-matching#phrasematcher

"""
import sys
sys.path.append(".")
import re
import spacy
from spacy.matcher import PhraseMatcher
from loguru import logger
from collections import defaultdict
import jieba
import jieba.posseg as pseg
import src.config_util as cfg 
from loguru import logger


# class Singleton(object):
#     """
#     Jieba Utils Class
#     """
#     _instance = None

#     def __new__(cls, *args, **kwargs):
#         if not cls._instance:
#             cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
#         return cls._instance


class SpacyEngSeg():
    """
    Spacy 英文分词
    """
    _spacy_seg_instance = None
    _spacy_matcher_instance = None

    def get_spacy_seg_instance(self):
        """get instande"""
        return self._spacy_seg_instance

    def get_spacy_matcher_instance(self):
        """get instance"""
        return self._spacy_matcher_instance
    
    def __init__(self,
                 user_dict_path=cfg.spacy_user_dict):
        """init"""
        if not self._spacy_seg_instance:
            logger.info("Loading spacy seg model and user dict, please wait ...")
            # 基础分词器
            nlp = spacy.load("en_core_web_sm")
            self._spacy_seg_instance = nlp
            # 匹配器
            matcher = PhraseMatcher(nlp.vocab)
            label2words = self.load_user_dict(user_dict_path)
            for label, words in label2words.items():
                patterns = [nlp.make_doc(text) for text in words]
                matcher.add(label, patterns) # label -> patterns
            self._spacy_matcher_instance = matcher
            logger.info("Loading Successfully !")

        # 默认标签 分别是: 药品 疾病 机构名 靶名
        self.default_tag_list = ["drug", "disease", "org", "target"]

    def load_user_dict(self, user_dict_path):
        """
        加载用户词典,和jieba格式一致
        txt每一行格式: "{word} {num} {label}"
        """
        re_userdict = re.compile('^(.+?)( [0-9]+)?( [a-z]+)?$', re.U)
        label2words = defaultdict(set)
        with open(user_dict_path) as f:
            for line in f.readlines():
                line = line.strip()
                word, freq, label = re_userdict.match(line).groups()
                if freq is not None:
                    freq = freq.strip()
                if label is not None:
                    label = label.strip()
                label2words[label].add(word)
        return label2words

    def recognize_entity(self, text, tag_list):
        """
        识别实体
        """
        if len(text) == 0:
            return []
        entity_list = []
        try:
            # 先做一次分词
            doc = self._spacy_seg_instance(text)
            # 根据分词结果按照matcher进行匹配合并
            matches = self._spacy_matcher_instance(doc)
            for match_id, start, end in matches:
                # label
                label = self._spacy_matcher_instance.vocab[match_id].text
                if label not in tag_list:
                    continue
                # text
                span = doc[start:end]
                entity = span.text # 自动合并字符串
                entity_list.append([entity, label])
        except Exception as e:
            logger.warning(f"recognize_entity error: {str(e)}")
        return entity_list


class Singleton(object):
    """
    Jieba Utils Class
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance


class JiebaSeg(Singleton):
    """
    Jieba Seg
    """
    _jieba_tokenizer_instance = None
    _jieba_postokenizer_instance = None

    def get_jieba_instance(self):
        """get instance"""
        return self._jieba_tokenizer_instance

    def get_jieba_pos_instance(self):
        """get instance"""
        return self._jieba_postokenizer_instance

    def __init__(self,
                 user_dict_path=cfg.jieba_user_dict):
        """init"""
        if not self._jieba_tokenizer_instance:
            # 基础分词器
            base_obj = jieba.Tokenizer()
            base_obj.load_userdict(user_dict_path)
            base_obj.tmp_dir = "./"
            self._jieba_tokenizer_instance = base_obj

        if not self._jieba_postokenizer_instance:
            # 词性分词器
            pos_jieba_obj = pseg.POSTokenizer(self._jieba_tokenizer_instance)
            pos_jieba_obj.initialize()
            self._jieba_postokenizer_instance = pos_jieba_obj

        # 默认标签 分别是: 药品 疾病 机构名 靶名
        self.default_tag_list = ["drug", "disease", "org", "target"]

    def add_words(self, dict_path):
        """
        add words
        """
        with open(dict_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                self._jieba_tokenizer_instance.add_word(word)


    def add_word(self, word, freq=None, tag=None):
        """
        add word
        """
        self._jieba_tokenizer_instance.add_word(word, freq=freq, tag=tag)


    def add_name_entity(self, dict_path):
        """
        add word
        """
        with open(dict_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().split(" ")[0]
                self._jieba_tokenizer_instance.add_word(word, freq=None, tag="PER")


    def recognize_entity(self, text, tag_list):
        """
        识别实体
        https://github.com/fxsjy/jieba
        """
        if len(text) == 0:
            return []
        entity_list = []
        try:
            result = self._jieba_postokenizer_instance.cut(text)
            for word, label in result:
                # print(word, label)
                if label in tag_list:
                    entity_list.append([word, label])
        except Exception as e:
            logger.warning(f"recognize_entity error: {str(e)}")
        return entity_list


    def recognize_name(self, text):
        """
        识别姓名
        """
        name_list = self.recognize_entity(text, tag_list=["nr", "PER"])
        real_name_list = []
        for name, tag in name_list:
            if name.startswith("小") \
                    or "宝宝" in name \
                    or "宝贝" in name \
                    or "孩子" in name \
                    or "可爱" in name:
                continue
            if len(name) < 2:
                continue
            if tag == "nr" and (len(name) > 3 or name[0] not in self.chinese_name_dict):
                continue
            real_name_list.append(name)
        return real_name_list


    def recognize_disease(self, text):
        """
        识别疾病
        """
        disease_list = self.recognize_entity(text, tag_list=["disease"])
        disease_list = [d[0] for d in disease_list]
        return disease_list


    def cut_for_search(self, text):
        """
        cut for search
        """
        return self._jieba_tokenizer_instance.cut_for_search(text)
        

    def cut(self, text):
        """
        cut
        """
        return self._jieba_tokenizer_instance.cut(text)


def is_chinese_or_english(content):
    """
    判断中文
    :param content:
    :return:
    """
    # 使用正则表达式匹配中文或英文字符
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]')
    # english_pattern = re.compile('[A-Za-z]')
    # 检查字符串是否包含中文字符
    if chinese_pattern.search(content):
        return 'zh'
    # 检查字符串是否包含英文字符
    else:
        return 'en'

        
def parse_doc_labels(title: str, zh_seg, en_seg):
    """
    文档标签抽取
    """
    # 第一部分，基础标签映射
    keyword_with_label = [
        ([
            r"说明书|适应症|成分|处方信息要点",
            r"INDICATIONS AND USAGE|HIGHLIGHTS OF PRESCRIBING INFORMATION"
        ], "说明书"),
        ([
            r"指南",
            r"PRACTICE|GUIDELINE",
        ], "指南"),
        ([
            r"专家共识|专家建议|共识|建议"
        ], "专家共识"),
        ([
            r"研究", 
            r"study|Renal Effects|clinical trial program|narrative review",
            r"trials|phase III trials|phase I trials|phase II trials"
        ], "临床研究"),
    ]
    title_low = title.lower()
    record_labels = set()
    label_map = dict()
    for keywords, label in keyword_with_label:
        keyword_re = "|".join([keyword.lower() for keyword in keywords])
        if re.search(keyword_re, title_low):
            record_labels.add(label)
            if "doc_type" not in label_map:
                label_map["doc_type"] = set()
                label_map["doc_type"].add(label)
    # 第二部分，分词后进行标签映射
    lang = is_chinese_or_english(title)
    if lang == "zh":
        title_seg = zh_seg.recognize_entity(title, tag_list=["drug", "disease", "department"])
    else:
        title_seg = en_seg.recognize_entity(title, tag_list=["drug", "disease", "department"])
    tag2label = {"drug": "药物", "disease": "疾病", "department" : "科室"}
    for word, tag in title_seg:
        if tag in tag2label:
            record_labels.add(word)
            if tag not in label_map:
                label_map[tag] = set()
        label_map[tag].add(word)

    # convert set to list
    for key, value in label_map.items():
        label_map[key] = list(value)

    return list(record_labels), label_map


if __name__ == "__main__":
    seg1 = SpacyEngSeg()
    seg2 = SpacyEngSeg()
    print(seg1 is seg2)
    a1 = seg1.get_spacy_seg_instance()
    a2 = seg2.get_spacy_seg_instance()
    print(a1 is a2)
    
    print(seg1.recognize_entity(
        text="2015 leqvio oncol-polarenal effects rr nhl or cll-.pdf",
        tag_list=["drug", "disease"],
    ))
    