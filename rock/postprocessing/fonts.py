# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
font。

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


from typing import List, Optional
import os
import requests

from src.rock.settings import settings


def get_font_path(langs: Optional[List[str]] = None) -> str:
    """get font path"""
    font_path = settings.RECOGNITION_RENDER_FONTS["all"]
    if langs is not None:
        for k in settings.RECOGNITION_RENDER_FONTS:
            if k in langs and len(langs) == 1:
                font_path = settings.RECOGNITION_RENDER_FONTS[k]
                break

    if not os.path.exists(font_path):
        os.makedirs(os.path.dirname(font_path), exist_ok=True)
        font_dl_path = f"{settings.RECOGNITION_FONT_DL_BASE}/{os.path.basename(font_path)}"

        with requests.get(font_dl_path, stream=True) as r, open(font_path, 'wb') as f:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return font_path