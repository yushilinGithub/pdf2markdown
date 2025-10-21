#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
run files offline.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from src.jungle.convert import convert_single_pdf
from src.jungle.logger import configure_logging
from src.jungle.models import load_all_models
from src.jungle.cleaners.ner import JiebaSeg, SpacyEngSeg, parse_doc_labels
import argparse

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str)
    args = parser.parse_args()
    model_lst = load_all_models()

    with open(args.input_file, "rb") as f:
        bfile = f.read()

    structure, language, knowledge_type = convert_single_pdf(bfile, model_lst)
    with open("result.md", "w") as f:
        f.write(structure.to_markdown())