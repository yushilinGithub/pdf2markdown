#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning) # Filter torch pytree user warnings

import pypdfium2 as pdfium # Needs to be at the top to avoid warnings
import pypdfium2.raw as pdfium_c
from PIL import Image
from loguru import logger

from src.jungle.utils import flush_cuda_memory
from src.jungle.tables.rock_table import format_tables
from src.jungle.debug.data import dump_bbox_debug_data
from src.jungle.layout.layout import layout, annotate_block_types
from src.jungle.layout.order import order, sort_blocks_in_reading_order
from src.jungle.ocr.lang import replace_langs_with_codes, validate_langs
from src.jungle.ocr.detection import line_detection
from src.jungle.ocr.recognition import run_ocr
from src.jungle.pdf.extract_text import get_text_blocks
from src.jungle.cleaners.headers import filter_header_footer
#from src.jungle.equations.equations import replace_equations
from src.jungle.pdf.utils import find_filetype
from src.jungle.postprocessors.editor import edit_full_text
from src.jungle.cleaners.code import identify_code_blocks, indent_blocks
from src.jungle.cleaners.bullets import replace_bullets
from src.jungle.cleaners.headings import split_heading_blocks
from src.jungle.cleaners.fontstyle import find_bold_italic
from src.jungle.postprocessors.markdown import merge_spans, merge_lines
from src.jungle.cleaners.text import cleanup_text
from src.jungle.images.extract import extract_images
from src.jungle.images.save import images_to_dict
from src.jungle.title.title_level import DynamicTitleParser
from src.jungle.schema.entity import KnowledgeType, Language
from src.jungle.ocr.heuristics import no_text_found
from src.jungle.cleaners.document_type import DocumentType
from src.jungle.cleaners.guideline_extracter import GuidelineExtracter
from src.jungle.structure.toc_title import MetaCateLog

from typing import List, Dict, Tuple, Optional, Union
from src.jungle.settings import settings
import src.config_util as cfg
import ftfy


def contain_garbage(pages):
    """
    判断编码是否正常，不正常利用 ocr
    """
    all_text = 0
    meaningness_text = 0
    for page in pages:
        for c in page.prelim_text:
            if ord(c) < 65:
                meaningness_text += 1
            all_text += 1

    return meaningness_text / all_text 

def get_num_unicode_map_error(doc):
    """
    get num unicode map error using pdfium
    """
    blocks = []
    num_unicode_map_error = 0
    for page_idx in range(len(doc)):
        page = doc.get_page(page_idx)
        text_page = page.get_textpage()
        total_chars = text_page.count_chars()

        for i in range(total_chars):
            char = pdfium_c.FPDFText_GetUnicode(text_page, i)
            has_unicodemap_error = pdfium_c.FPDFText_HasUnicodeMapError(text_page, i)
            if has_unicodemap_error != 0:
                num_unicode_map_error += 1
    return num_unicode_map_error


def convert_single_pdf(
        document: Union[str, bytes],
        model_lst: List,
        langs: Optional[List[str]] = None,
        batch_multiplier: int = 1
) -> Tuple[str, Dict[str, Image.Image], Dict]:
    """convert single pdf to markdown"""
    if langs is None:
        langs = ["English", "Chinese"] 
    # Set language needed for OCR
    if langs is None:
        langs = [settings.DEFAULT_LANG]

    langs = replace_langs_with_codes(langs)
    validate_langs(langs)

    # Find the filetype
    filetype = find_filetype(document)

    # Setup output metadata
    out_meta = {
        "languages": langs,
    }


    # Get initial text blocks from the pdf
    doc = pdfium.PdfDocument(document)

    pages, toc = get_text_blocks(
        doc,
        document
    )

    out_meta.update({
        "toc": toc,
        "pages": len(pages),
    })

    num_unicode_map_error = get_num_unicode_map_error(doc)
    if num_unicode_map_error > 10:
        logger.warning(
            f"Unicode map error found in {num_unicode_map_error} chars, "
            "this may cause some text to be garbled."
        )
    else:
        logger.info("Unicode map error found in 0 chars, "
                      "this pdf is great")

    layout_model, order_model, detection_model, ocr_model, table_model = model_lst

    if no_text_found(pages) or contain_garbage(pages) > 0.5 or num_unicode_map_error > 150: # No text found on any page then we need to OCR
        logger.info("No text has been found, or unicode map error is found, "
                    "so OCR will be used to get text, which may take some time.")
        line_detection(doc, pages, detection_model, batch_multiplier=batch_multiplier)
        flush_cuda_memory()

        # OCR pages as needed

        pages, ocr_stats = run_ocr(doc, pages, langs, ocr_model, batch_multiplier=batch_multiplier)
        flush_cuda_memory()

        out_meta["ocr_stats"] = ocr_stats    

    logger.info(f"start layout prediction, length of pdfs is {len(pages)}")
    mean_intersection_pct = layout(doc, pages, layout_model, batch_multiplier=batch_multiplier)
    logger.info(f"finish layout prediction, {mean_intersection_pct}")
    
    flush_cuda_memory()
    # Find headers and footers
    bad_span_ids = filter_header_footer(pages)
    out_meta["block_stats"] = {"header_footer": len(bad_span_ids)}

    # Add block types in
    #annotate_block_types(pages)
    # assign_textline_to_layout(pages)
    # Dump debug data if flags are set
    dump_bbox_debug_data(doc, document, pages)

    # Find reading order for blocks
    logger.info("start reading order prediction")
    order(doc, pages, order_model, batch_multiplier=batch_multiplier)
    logger.info("finish reading order prediction")
    #sort_blocks_in_reading_order(pages)
    flush_cuda_memory()


    if cfg.SHOULD_PARSE_TABLE:
        logger.info("start table structure prediction")
        pages = format_tables(pages, table_model)
        logger.info("finish table structure prediction")

    for page in pages:
        for block in page.blocks:
            block.filter_spans(bad_span_ids)
            block.filter_bad_span_types()

    # filtered, eq_stats = replace_equations(
    #     doc,
    #     pages,
    #     texify_model,
    #     batch_multiplier=batch_multiplier
    # )
    # flush_cuda_memory()
    # out_meta["block_stats"]["equations"] = eq_stats

    # Extract images and figures
    #if settings.EXTRACT_IMAGES:
    #    extract_images(doc, pages)

    # Split out headers
    split_heading_blocks(pages)
    find_bold_italic(pages)

    # Copy to avoid changing original data
    merged_lines = merge_spans(pages)
    structure = merge_lines(merged_lines)
    
    meta_cate_log = MetaCateLog(toc)
    doc_type = DocumentType(pages)

    if doc_type.language == Language.CHINESE.value and doc_type.document_type == KnowledgeType.GUIDELINE.value:
        logger.info("guideline extracter")
        guideline_extracter = GuidelineExtracter()
        guideline_extracter.extract(structure)
        logger.info("finish guideline extracter")

    if doc_type.language == Language.CHINESE.value:
        logger.info("Chinese document, will try to parse title level")
        title_parser = DynamicTitleParser()
        structure = title_parser.predict(structure, doc_type.document_type)

    elif doc_type.language == Language.ENGLISH.value and meta_cate_log:
        logger.info("English document, will try to parse title level, with its own title")
        structure = meta_cate_log.assign_title_level(structure)
    
    else:
        logger.info(" will try to parse title level, with layout model predict")
        structure.self_title_assign()

    return structure, doc_type.language, doc_type.document_type