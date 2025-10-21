#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file parse
"""
import json
import base64
import asyncio
import traceback

from typing import List, Dict
from loguru import logger
from datetime import datetime, timezone


import sys
import os
#sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


from src import connect
from src.connect.download import download
import src.config_util as cfg
from src.connect.connection import PgConnection
from src.connect.minio import save_to_minio
from src.jungle.schema.entity import ParseStatus, DocType
from src.error.errors import RepeatedParseException, FileUrlException, UploadBosException

from src.jungle.convert import convert_single_pdf
from src.jungle.logger import configure_logging
from src.jungle.models import load_all_models
from src.jungle.cleaners.ner import JiebaSeg, SpacyEngSeg, parse_doc_labels


class FileParse:
    """
    FileParse
    """
    def __init__(self):
        """
        init load all model
        """
        self.model_lst = load_all_models()
        #self.zh_seg = JiebaSeg()
        #self.en_seg = SpacyEngSeg()

    def parse_files(self, file_datas: List[Dict]):
        """
        parse files
        """
        res = []
        for file_data in file_datas:
            labels = []
            try:
                labels = self.parse_file(file_data)
                res.append({
                    "file_id": file_data["file_id"],
                    "type": file_data.get("type", ""),
                    "file_name": file_data.get("file_name", ""),
                    "file_type": file_data.get("file_type", ""),
                    "kg_id": file_data.get("kg_id", ""),
                    "catalog_id": file_data.get("catalog_id", ""),
                    "account_id": file_data.get("account_id", ""),
                    "user_id": file_data.get("user_id", ""),
                    "parse_status": 2,
                    "parse_fail": "",
                    "label": labels
                })

            except RepeatedParseException as e:
                logger.error(f"repeated parse, error: {e}")
                logger.error(traceback.format_exc())
                res.append({
                    "file_id": file_data["file_id"],
                    "type": file_data.get("type", ""),
                    "file_name": file_data.get("file_name", ""),
                    "file_type": file_data.get("file_type", ""),
                    "kg_id": file_data.get("kg_id", ""),
                    "catalog_id": file_data.get("catalog_id", ""),
                    "account_id": file_data.get("account_id", ""),
                    "user_id": file_data.get("user_id", ""),
                    "parse_status": ParseStatus.PROCESSING,
                    "parse_fail": "文档解析中，请勿重复提交解析。"
                })

            except FileUrlException as e:
                logger.error(f"repeated parse, error: {e}")
                logger.error(traceback.format_exc())
                res.append({
                    "file_id": file_data["file_id"],
                    "type": file_data.get("type", ""),
                    "file_name": file_data.get("file_name", ""),
                    "file_type": file_data.get("file_type", ""),
                    "kg_id": file_data.get("kg_id", ""),
                    "catalog_id": file_data.get("catalog_id", ""),
                    "account_id": file_data.get("account_id", ""),
                    "user_id": file_data.get("user_id", ""),
                    "parse_status": ParseStatus.FAILED,
                    "parse_fail": "下载文件失败，请查看 fileurl 是否有效！"
                })

            except UploadBosException as e:
                logger.error(f"repeated parse, error: {e}")
                logger.error(traceback.format_exc())
                res.append({
                    "file_id": file_data["file_id"],
                    "type": file_data.get("type", ""),
                    "file_name": file_data.get("file_name", ""),
                    "file_type": file_data.get("file_type", ""),
                    "kg_id": file_data.get("kg_id", ""),
                    "catalog_id": file_data.get("catalog_id", ""),
                    "account_id": file_data.get("account_id", ""),
                    "user_id": file_data.get("user_id", ""),
                    "parse_status": ParseStatus.FAILED,
                    "parse_fail": "抱歉，文档解析结果存储失败，我们正在加急处理，很抱歉影响您的体验！"
                })

            except Exception as e:
                logger.error(f"parse file failed: {file_data}, error: {e}")
                logger.error(traceback.format_exc())
                res.append({
                    "file_id": file_data["file_id"],
                    "type": file_data.get("type", ""),
                    "file_name": file_data.get("file_name", ""),
                    "file_type": file_data.get("file_type", ""),
                    "kg_id": file_data.get("kg_id", ""),
                    "catalog_id": file_data.get("catalog_id", ""),
                    "account_id": file_data.get("account_id", ""),
                    "user_id": file_data.get("user_id", ""),
                    "parse_status": ParseStatus.FAILED,
                    "parse_fail": "PDF文件中包含了特殊的加密保护或非标准的对象结构，建议您查看文档后重新上传解析。"
                })
        return res

    def parse_pdf_http(self, file_data: Dict):
        """
        上传pdf 解析，通过http方式
        """

        try:
            json_tree, markdown, debug_images = self.parse_pdf(file_data)
            return {
                "json_tree": json_tree,
                "markdown": markdown,
                "parse_status": 2,
                "parse_fail": "",
                "debug_images": debug_images}   
        except FileUrlException as e:
            logger.error(f"file url error, error: {e}")
            logger.error(traceback.format_exc())
            return {
                "json_tree": {},
                "markdown": "",
                "debug_images": [],
                "parse_status": ParseStatus.FAILED,
                "parse_fail": "下载文件失败，请查看 fileurl 是否有效！"
            }
        except Exception as e:
            logger.error(f"parse file failed: {file_data.get('url', '')}, error: {e}")
            logger.error(traceback.format_exc())
            return {
                "json_tree": {},
                "markdown": "",
                "debug_images": [],
                "parse_status": ParseStatus.FAILED,
                "parse_fail": "PDF文件中包含了特殊的加密保护或非标准的对象结构，建议您查看文档后重新上传解析。"
            }


    def parse_pdf(self, file_data: Dict):
        """
        parse pdf
        """
        
        if file_data.get('url', ""):
            byte_content = download(file_data["url"])
            if not byte_content: 
                logger.error(f"file url error, mq: {file_data}")
                raise FileUrlException
        elif file_data.get('file_content', ""):
            pdf_stream = file_data['file_content']
            if isinstance(pdf_stream, str):
                byte_content = base64.b64decode(pdf_stream)
        else:
            raise FileUrlException

        debug_image = file_data.get("debug_image", False)
        if debug_image:
            structure, language, knowledge_type, debug_images = convert_single_pdf(byte_content, 
                                                                    self.model_lst,
                                                                    debug=debug_image)
            json_tree =  structure.to_tree(filename=file_data.get("file_name", ""))
            markdown = structure.to_markdown()
            return json_tree, markdown, debug_images
        else:
            structure, language, knowledge_type = convert_single_pdf(byte_content, 
                                                                    self.model_lst,
                                                                    debug=False)
            json_tree =  structure.to_tree(filename=file_data.get("file_name", ""))
            markdown = structure.to_markdown()
            return json_tree, markdown, []

        # pdf_stream = file_data["file_content"]
        # if isinstance(pdf_stream, str):
        #     pdf_stream = base64.b64decode(pdf_stream)
        # structure, language, knowledge_type = convert_single_pdf(pdf_stream, self.model_lst)
        # json_tree =  structure.to_tree(filename=file_data["file_name"])
        # markdown = structure.to_markdown()
        # return json_tree, markdown


    def parse_file(self, file_data: Dict):
        """
        parse file
        """
        with connect.conn_pool as conn:
            #file_object_name = cls._get_object_name(conn, file_data["file_id"])
            parse_status = self._get_status(conn, file_data["file_id"])
            if parse_status and parse_status not in (ParseStatus.FAILED, ParseStatus.PREPARE, ParseStatus.SUCCESS):
                raise RepeatedParseException(-1, "please do not call repeatedly", None)

            if parse_status == ParseStatus.SUCCESS:
                return []

            if not parse_status:
                sql = """
                INSERT INTO 
                    structured_parsed_result (file_id, file_type, file_url, parse_status, update_time)
                VALUES 
                    (%s, %s, %s, %s, %s)
                """
                conn.execute(sql, [
                    file_data["file_id"], 
                    file_data["file_type"], 
                    file_data["url"], 
                    ParseStatus.PROCESSING, 
                    datetime.now()
                ])
            else:
                sql = """
                UPDATE 
                    structured_parsed_result 
                SET
                    file_type = %s,
                    file_url = %s,
                    parse_status = %s,
                    update_time = %s
                WHERE parse_status = %s AND file_id = %s;
                """
                rowcount = conn.execute_rowcount(sql, [
                    file_data["file_type"], 
                    file_data["url"], 
                    ParseStatus.PROCESSING, 
                    datetime.now(), parse_status, 
                    file_data["file_id"]
                ])
                if rowcount != 1:
                    raise Exception("update ocr file failed")

        
        # common ocr parse
        byte_content = download(file_data["url"])

        if not byte_content:
            
            with connect.conn_pool as conn:
                conn.execute("update structured_parsed_result set parse_status=%s where file_id=%s", [
                    ParseStatus.FAILED, 
                    file_data["file_id"]
                ])
            logger.error(f"file url error, mq: {file_data}")
            raise FileUrlException

        # common ocr parse
        structure, language, knowledge_type = convert_single_pdf(byte_content, self.model_lst)
        
        markdown = structure.to_markdown().encode('utf-8')
        
        if len(markdown) < 6:
            raise ScanPdfException

        try:

            json_tree_byte =  json.dumps(structure.to_tree(filename=file_data["file_name"])).encode('utf-8')
            json_tree_url = save_to_minio(json_tree_byte, 
                            file_data["user_id"],
                                file_data["account_id"],
                            f"{file_data['file_id']}_tree.json")
            #mock a url , 
            markdown_url = save_to_minio(markdown, 
                                        file_data["user_id"], 
                                        file_data["account_id"], 
                                        f"{file_data['file_id']}_markdown.md")

            labels, label_map = parse_doc_labels(file_data["file_name"], zh_seg=self.zh_seg, en_seg=self.en_seg)


        except Exception as e:
            with connect.conn_pool as conn:
                conn.execute("update structured_parsed_result set parse_status=%s where file_id=%s", [
                    ParseStatus.FAILED, 
                    file_data["file_id"]
                ])
            raise UploadBosException


        with connect.conn_pool as conn:
            conn.execute("begin;")
            now = datetime.now()

            sql = """
            INSERT INTO 
                structured_parsed_result (file_id, kg_id, file_type, file_name, file_url, language, knowledge_type, parse_status, json_tree_url, markdown_url, feature, update_time)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_id) DO 
                UPDATE SET 
                    kg_id = EXCLUDED.kg_id,
                    file_type = EXCLUDED.file_type,
                    file_name = EXCLUDED.file_name,
                    file_url = EXCLUDED.file_url,
                    language = EXCLUDED.language,
                    knowledge_type = EXCLUDED.knowledge_type,
                    parse_status = EXCLUDED.parse_status,
                    json_tree_url = EXCLUDED.json_tree_url,
                    markdown_url = EXCLUDED.markdown_url,
                    feature = EXCLUDED.feature,
                    update_time = EXCLUDED.update_time;
            """
            
            result = conn.execute(
                sql, 
                [file_data["file_id"], 
                file_data.get("kg_id", ""),
                file_data["file_type"],
                file_data["file_name"], 
                file_data["url"], 
                language,
                knowledge_type,
                ParseStatus.SUCCESS,
                json_tree_url,
                markdown_url,
                json.dumps(label_map),
                now]
            )
            if result.rowcount != 1:
                raise Exception("insert structured parsed result failed")

        return labels
    
    #def parse_file_http(self, file_data: Dict)
    
    @classmethod
    def _get_object_name(cls, conn: PgConnection, file_id: str):
        """
            获取文件对应的对象名称，如果不存在则返回None。
        该方法仅用于内部类方法，请勿直接调用。
        
        Args:
            conn (PgConnection): PostgreSQL数据库连接对象，必须是公共连接。
            file_id (str): 文件ID，字符串格式。
        
        Returns:
            Optional[str]: 返回文件对应的对象名称，如果不存在则返回None。
        
        Raises:
            无。
        """
        sql = "SELECT object_name FROM public.doc WHERE id=%s"
        r = conn.fetchone(sql, [int(file_id)])
        # r = conn.fetchone(sql, [])
        return r.object_name
        


    @classmethod
    def _get_status(cls, conn: PgConnection, file_id: str):
        """
            获取文件的解析状态，如果不存在则返回None。
        参数：
            - conn (PgConnection) - PostgreSQL连接对象
            - file_id (str) - 文件ID字符串
        返回值（Optional[str]）- 解析状态字符串，可能为None，表示文件不存在或未被解析过
        """
        sql = "SELECT parse_status FROM structured_parsed_result WHERE file_id=%s"
        r = conn.fetchone(sql, [file_id])
        if r:
            return r.parse_status
        return None

# if __name__ == "__main__":

#     file = {"url": "http://localhost:8000/鼻咽癌外科治疗专家共识.pdf", 
#               "file_id":"1234", "file_name":"鼻咽癌外科治疗专家共识.pdf", 
#               "file_type": "pdf", "user_id": "404764182849", "account_id": "11", "kg_id": "20"}

#     result = FileParse.parse_files([file])
#     print("-----result", result)