#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
doc string
"""

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, stop_after_delay
from src import config_util as cfg
from loguru import logger
from typing import List
import io


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3)
    )
def save_to_bos(upload_file: bytes, user_id: str, account_id: str, object_name: str, filename: str):
    """
    存储到bos
    """

    map_to_source = {"public/undefined": 0,
                    "public/kg": 1,
                    "private/doc": 2,
                    "public/h5": 3,
                    "public/built-in": 4,
                    "private/attach": 5}

    prefix = "/".join(object_name.split("/")[:2])

    if prefix in map_to_source:
        register = map_to_source[prefix]
    else:
        logger.info(f"{prefix} is the prefix of {object_name} is not correct!!")
        register = 5

    # 百草文档的内置文档，传到用户的私域
    if object_name.startswith("public/built-in/examples"):
        register = 2

    in_memory_file = io.BytesIO(upload_file)
    in_memory_file.name = filename



    # k8s：集群内的service name地址
    bot_server_host = cfg.BOS_SERVER_HOST
    router = "/api/01bot/server/v2/storage/bos/object"  # 不变
    url = bot_server_host + router
    headers = {'X-IHU-AccountID': account_id, 'X-IHU-UserID': user_id}  # 必须
    files = {
        "upload_files" : in_memory_file,
    }
    logger.info(f"上传bos {url}")
    # 前端根据场景填写；策略填写5
    values = {
        "register": register,  # 0：未知来源，1：企业知识库，2：个人知识库，3：h5端，4：内置，5：附件
    }
    response = requests.post(url, headers=headers, files=files, data=values).json()
    if response["message"] != "success":
        raise Exception(f"上传bos 失败 {response}")

    else:
        return response["data"][0]["object_name"]

