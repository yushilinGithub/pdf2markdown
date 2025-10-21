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
def save_to_minio(upload_file: bytes, user_id: str, account_id: str, filename: str):
    """
    存储到minio

    curl --location --request POST '/cdss/standard/server-go/manage/upload' \
        --header 'X-IHU-AccountID: 123' \
        --header 'X-IHU-UserID: 47' \
        --header 'User-Agent: iAPI/1.0.0 (http://iapi.baidu-int.com)' \
        --form 'file=@"/Users/shishuai04/Desktop/昆仑芯加速卡测试指导_V1.0.pdf"'
    """

    in_memory_file = io.BytesIO(upload_file)
    in_memory_file.name = filename

    # k8s：集群内的service name地址
    minio_server_host = cfg.CDSS_SERVER_URL
    router = "/cdss/standard/server-go/manage/upload"  # 不变
    url = minio_server_host + router
    headers = {'X-IHU-AccountID': account_id, 'X-IHU-UserID': user_id, 
                'User-Agent': 'iAPI/1.0.0 (http://iapi.baidu-int.com)'}  # 必须
    files = {
        "file" : in_memory_file,
    }
    logger.info(f"上传 minio {url}, {filename}")
    # 前端根据场景填写；策略填写5

    response = requests.post(url, headers=headers, files=files).json()
    if response["message"] != "success":
        logger.info(f"{response}")
        raise Exception("上传bos 失败")
    
    else:
        file_id = response["result"][0]["file_id"]
        return f"{minio_server_host}/cdss/standard/server-go/manage/download/{file_id}"

