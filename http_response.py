#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
doc string
"""

import json
import time

from loguru import logger


from src.jungle.schema.entity import FragmentStatus

from src.jungle.convert import convert_single_pdf
from src.jungle.logger import configure_logging
from src.jungle.models import load_all_models
from src.jungle.cleaners.ner import JiebaSeg, SpacyEngSeg, parse_doc_labels
from src.file_parse import FileParse


class HTTPResponse(object):
    """
    http response
    """

    def __init__(self):
        
        # self.model_lst = load_all_models()
        # self.zh_seg = JiebaSeg()
        # self.en_seg = SpacyEngSeg()
        self.pdf_parser = FileParse()

    def _parse_pdf(self, book_data):
        """
        文档解析状态 0未解析，2成功，3失败
        :params book_data: dict
        return:
            status, err_msg
        """
        # 解析
        logger.info("[start] parse pdf...")
        parsed_data = self.pdf_parser.parse_pdf_http(book_data)
        logger.info("[complete] parse pdf...")
        
        return parsed_data

    def get_file_parse_response(self, query_data):
        """
        :params query_data: dict
        """
        books_status = []
        books = query_data.get("files", [])
        for book_data in books:
            info = {
                "type": book_data["type"],
                "file_id": book_data["file_id"],
                "parse_status": book_data.get("parse_status", 0),
                "parse_fail": "",
                "label": [],
                "abstract": "",
                "abstract_ch": "",
                "conclusion": "",
                "conclusion_ch": "",
                "drug": [],
                "disease": [],
                "doc_type": [],
                "department": []
            }
            
            try:
                parse_data = self._parse_pdf(book_data)
                info["parse_status"] = parse_data["parse_status"]
                info["parse_fail"] = parse_data["parse_fail"]
                info["label"] = parse_data["label"]
                for k, v in parse_data.get("label_map", {}).items():
                    info[k] = list(v)
                logger.info(f"[File-parse] status: {json.dumps(info, ensure_ascii=False)}")
            except Exception as e:
                info["parse_status"] = 3 # 0未解析，2成功，3失败
                info["parse_fail"] = f"parse error: {str(e)}"
                logger.warning(f"[File-parse] status: {json.dumps(info, ensure_ascii=False)}")
            
            books_status.append(info)
        return books_status
