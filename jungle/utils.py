#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import torch
import time
import src.config_util as cfg
from loguru import logger
import fitz
from fontTools.ttLib import TTFont
from io import BytesIO
from PIL import Image, ImageDraw 
import base64



def flush_cuda_memory():
    """
    flush cuda memory to avoid OOM error caused by large model size.
    """
    if cfg.DEVICE == "cuda":
        torch.cuda.empty_cache()


def cal_time(func):
    """
    时间
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        """
        wrapper
        """
        ts = time.time()
        result = func(*args, **kwargs)
        te = time.time()
        logger.info("[TIME] %s time elapsed: %s secs." % (func.__name__, te - ts))
        return result

    return wrapper


def is_chinese_character(char):
    """检查字符是否为中文字符"""
    code_point = ord(char)
    return (
        (0x4E00 <= code_point <= 0x9FFF) or      # 基本汉字
        (0x3400 <= code_point <= 0x4DBF) or      # 扩展 A 区
        (0x20000 <= code_point <= 0x2A6DF) or    # 扩展 B 区
        (0x2A700 <= code_point <= 0x2B73F) or    # 扩展 C 区
        (0x2B740 <= code_point <= 0x2B81F) or    # 扩展 D 区
        (0x2B820 <= code_point <= 0x2CEAF) or    # 扩展 E 区
        (0x2CEB0 <= code_point <= 0x2EBEF) or    # 扩展 F 区
        (0xF900 <= code_point <= 0xFAFF) or      # 兼容汉字
        (0x2F800 <= code_point <= 0x2FA1F)       # 兼容汉字补充
    )

font_white_list = [
    "Times-Roman",
    "Times New Roma",
    "Helvetica",
    "SimSun",
    "SimHei"
]

font_black_list = [
    "FzBookMaker",
    "宋体",
    "ËÎÌå",
    "ËÎÌå-GBK-EUC-",
    "宋体-GBK-EUC-",
    "EU-BZ+Z",
    "STSong-Light",
    "NBCDEE+E-BZ",
    "B4+SimSun",
    "B6+SimSun",
    "AAAAAQ+FZFSK--GBK1-0",
    "AAAAAY+FZFSK--GBK1-0",
    "FHFDIG+E-BZ",
    "E-BZ-PK74818f",
    "E-HZ-PK7481d5",
    "E-BX-PK74818c",
]


def black_list_check(font_name):
    """
    check font are in black list
    """
    for f in font_black_list:
        if f in font_name:
            return True
    return False


def check_font_is_support(file_bytes):
    """
    check pdf file's font support
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    seen = set()
    block_font = set()
    invalid_char = 0
    for page_num in range(len(doc)):
        invalid_cmap_fonts = []
        page = doc[page_num]
        for (xref, _, type, name, _, encoding) in page.get_fonts():
            if black_list_check(name):
                if "ËÎÌå-GBK-EUC-" in name:
                    name = "ËÎÌå"
                if "NBCDEE+E-BZ" in name:
                    name = "E-BZ"
                invalid_cmap_fonts.append(name)
        

        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block.keys():
                continue    
            for line in block["lines"]:
                for span in line["spans"]:
                    font = span["font"]

                    block_font.add(font)

                    if any([font in invalid_cmap_font for invalid_cmap_font in invalid_cmap_fonts]):
                        invalid_char += len(span["text"])
    logger.warning(f"invalid cmap fonts: {invalid_cmap_fonts}")
    logger.info(f"block_font {block_font}")
    logger.info(f"invalid_char {invalid_char}")
    if invalid_char > 5:
        return False
    else:
        return True


def remove_watermark(file_bytes):
    """remove watermark"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    # delete text watermark


    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        retoted_found = False
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                        
                    if "dir" in line and line["dir"][0] != 0.0 and line["dir"][0] != 1.0:
                        retoted_found = True
                        dir = line["dir"]
                        cosine = round(dir[0], 5)
                        sine = round(dir[1], 5)
                        cos_text = str(cosine).encode()
                        sin_text = str(sine).encode()
        xrefs = page.get_contents()
        for xref in xrefs:
            cont_lines = doc.xref_stream(xref).splitlines()
            changed = 0
            # remove all /Artifact /Watermark lines
            i = 0
            while i < len(cont_lines):
                line = cont_lines[i]
                

                if line.startswith(b"/Artifact") and b"/Watermark" in line:
                    if b"EMC" in cont_lines[i + 1: i + 50]:  
                        # this was not for us
                        j = cont_lines.index(b"EMC", i)
                        for k in range(i, j):
                            # look for image / xobject invocations in this line range
                            do_line = cont_lines[k]
                            cont_lines[k] = b""  # remove / empty this line
                            changed += 1
                        i = j
                    elif b"EMC " in cont_lines[i + 1:i + 50]: # this was not for us
                        j = cont_lines.index(b"EMC ", i)
                        for k in range(i, j):
                            # look for image / xobject invocations in this line range
                            do_line = cont_lines[k]
                            cont_lines[k] = b""  # remove / empty this line
                            changed += 1
                        i = j
                if line == b'BT' and b'ET' in cont_lines[i + 1: i + 50]:
                    j = cont_lines.index(b'ET', i)
                    for k in range(i, j):
                        # look for image / xobject invocations in this line range
                        do_line = cont_lines[k]
                        if retoted_found and cos_text in do_line and sin_text in do_line:
                            for k in range(i, j):
                                cont_lines[k] = b""  # remove / empty this line
                                changed += 1
                            break
                    i = j
                
                i = i + 1
            new_lines = [x for x in cont_lines if x != b""]
            if changed > 0:  # if we did anything, write back modified /Contents
                logger.info("update stream")
                doc.update_stream(xref, b"\n".join(new_lines))
    logger.info("finish remove text watermark")
    # delete image workmark

    image_dict = {}
    if len(doc) > 1:
        for page in doc: 
            img_list = page.get_images()
            for img in img_list:
                if img[4] == 1:
                    continue
                (xref, smask, width, height, bpc, colorspace, alt, colorspace, name) = img

                img_rects = page.get_image_rects(xref)
                if img_rects:
                    img_rect = img_rects[0]
                    if int(img_rect.x0) == 0  and int(img_rect.y0) == 0 and \
                        int(img_rect.x1) == int(page.rect.width) and int(img_rect.y1) == int(page.rect.height):
                        continue

            
                image_info = str((width, height, bpc, name))
                if image_info in image_dict:
                    image_dict[image_info] += 1
                else:
                    image_dict[image_info] = 1
        watermarks = []
        for img, number in image_dict.items():
            if number >= len(doc):
                watermarks.append(img)

        for page in doc:
            img_list = page.get_images()
            for img in img_list:
                (xref, smask, width, height, bpc, colorspace, alt, colorspace, name) = img
                image_info = str((width, height, bpc, name))
                if image_info in watermarks:
                    page.delete_image(xref)
    logger.info("finish remove image watermark")
    return doc.tobytes()


def debug_pdf(pages):
    """
    debug pdf
    """
    save_images = []
    buffers = []
    for page in pages:
        drawing_image = page.page_image.copy()
        drawing = ImageDraw.Draw(drawing_image)
        for posid, block in enumerate(page.blocks):
            drawing.rectangle(block.bbox, outline="red")
            drawing.text((block.bbox[0], block.bbox[1] - 10), str(posid) + "_" + block.block_type, fill="red")
        


        buffer = BytesIO()
        drawing_image.save(buffer, format='PNG')

        # Get the byte data from BytesIO
        image_bytes = buffer.getvalue()

        # Convert byte data to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        buffers.append(image_base64)
        
    return {"file_bytes": buffers}
