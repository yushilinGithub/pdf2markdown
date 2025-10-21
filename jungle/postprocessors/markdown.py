#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
postprocess script.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""


from src.jungle.schema.merged import MergedLine, MergedBlock, FullyMergedBlock
from src.jungle.schema.page import Page
from src.jungle.structure import Element, PDFStructure, AttrNorm
from src.jungle.utils import is_chinese_character
import src.config_util as cfg

import re
import regex
from typing import List
import string

def is_only_punctuation(s):
    """Check if text is only punctuation"""
    # Define punctuation and whitespace characters using string.punctuation
    punctuation_pattern = re.compile(r'^[{} \t\n\r\f\v]+$'.format(re.escape(string.punctuation + \
                                      					"。？，！：（）【】《》——“”‘’")),
                                       re.UNICODE)    
    # Strip spaces and check if the remaining string consists only of punctuation
    stripped_s = s.replace(" ", "")
    
    return bool(punctuation_pattern.match(stripped_s))


def escape_markdown(text):
    """ escape markdown mark"""
    # List of characters that need to be escaped in markdown
    characters_to_escape = r"[#]"

    # Escape each of these characters with a backslash
    escaped_text = re.sub(characters_to_escape, r'\\\g<0>', text)
    return escaped_text


def get_ratio(p1, p2):
    """get ration of two height"""
    h1, h2 = p1[1] - p1[0], p2[1] - p2[0]
    intersection = min(p2[1], p1[1]) - max(p2[0], p1[0]) 
    max_h = max(h1, h2)
    ratio = intersection / (max_h + 0.0001)
    return ratio
    

def center_offset(p1, p2):
    """
    get center offset ratio
    """
    h1, h2 = p1[1] - p1[0], p2[1] - p2[0]
    c1, c2 = (p1[1] + p1[0]) / 2, (p2[1] + p2[0]) / 2
    ratio = abs(c2 - c1) / max(h1, h2)
    return ratio


def sub_super_scribe(text):
    """"check if text is sub or super scripe"""
    
    # 这是一个简单的转义函数，它可能不完整，但可以作为起点  
    non_script_text = "&%$#_}{~^【】？～、，；：;:,。》><《￥`·()、"
    if len(text.strip()) > 9:
        return False
    if len(re.findall(r'[A-Z]', text)) > 3:
        return False
    if len(re.findall(r'[a-z]', text)) > 4:
        return False
    if is_only_punctuation(text):
        return False
    if len(re.findall(r'[\u4e00-\u9fa5\.]', text)) > 0:
        return False
    for non_script_char in non_script_text:
        if non_script_char in text:
            return False
    return True


def get_height_diff_ratio(p1, p2):
    """get height diff ratio"""
    h1, h2 = p1[1] - p1[0], p2[1] - p2[0]
    min_h, max_h = min(h1, h2) , max(h1, h2)
    ratio = (max_h - min_h) / max_h
    return ratio


def get_line_text(line):
    """
    get text of the line, and add latex for superscript and subscript
    """
    chars = []
    result_text = ""

    for span in line.spans:   
        if span.chars and int(span.rotation) == 0:
            chars.extend(span.chars)
        else:
            result_text += span.text
    
    for charid, char in enumerate(chars):
        if char["char"] in ["（", '《', "("] and charid < len(chars) - 1 and chars[charid + 1]["char"] == "]":
            cur_char = chars[charid]
            chars[charid] = chars[charid + 1]
            chars[charid + 1] = cur_char

    
    group_y0, group_y1 = None, None
    
    group_text = ""
    

    cur_pos = 0 # center ,1: belower, -1 upper 
    for charid, char in enumerate(chars):
        if char["char"] in ["\r", '\n']:
            continue
        y0, y1 = char["bbox"][1], char["bbox"][3]
        char_height = y1 - y0
        if group_y0 is None:
            if y1 - y0 != 0 and not char["char"] in ["　", " "]:
                group_y0, group_y1 = y0, y1
                group_height = y1 - y0
                group_text += char["char"]
            else: 
                group_text += char["char"]
        else:
            intersection = get_ratio((y0, y1), (group_y0, group_y1))
            height_diff_ratio = get_height_diff_ratio((y0, y1), (group_y0, group_y1))
            
            if intersection > 0.65 or y1 - y0 == 0 or char["char"] in ["　", " "]:
                #or height_diff_ratio < 0.4:
                group_text += char["char"]
            else:

                if char_height > group_height:
                    cur_pos = 0
                    char_center = (y1 + y0) / 2
                    group_center = (group_y1 + group_y0) / 2
                    if group_center > char_center:
                        if sub_super_scribe(group_text):
                            result_text += "$_{grouptext_placeholder}$".replace("grouptext_placeholder", group_text) 
                        else:
                            result_text += group_text
                    else:
                        if sub_super_scribe(group_text):
                            result_text += "$^{grouptext_placeholder}$".replace("grouptext_placeholder", group_text)
                        else:
                            result_text += group_text
                else:
                    result_text += group_text
                    
                    char_center = (y1 + y0) / 2
                    group_center = (group_y1 + group_y0) / 2
                
                    cur_pos = 1 if char_center > group_center else -1
                group_y0, group_y1 = y0, y1
                group_height = y1 - y0
                group_text = char["char"]

            
    group_text = group_text.encode('utf-8', 'ignore').decode('utf-8') 
    if cur_pos == 0:
        result_text += group_text
    elif cur_pos == 1:
        if sub_super_scribe(group_text):
            result_text += "$_{grouptext_placeholder}$".replace("grouptext_placeholder", group_text) 
        else:
            result_text += group_text
    elif cur_pos == -1:
        if sub_super_scribe(group_text):
            result_text += "$^{grouptext_placeholder}$".replace("grouptext_placeholder", group_text)
        else:
            result_text += group_text
    result_text.replace("~", "\~")
    return result_text

def surround_text(s, char_to_insert):
    """surround text"""
    leading_whitespace = re.match(r'^(\s*)', s).group(1)
    trailing_whitespace = re.search(r'(\s*)$', s).group(1)
    stripped_string = s.strip()
    modified_string = char_to_insert + stripped_string + char_to_insert
    final_string = leading_whitespace + modified_string + trailing_whitespace
    return final_string


def merge_spans(pages: List[Page]) -> List[List[MergedBlock]]:
    """merge spans"""
    merged_blocks = []
    for pagenum, page in enumerate(pages):
        page_blocks = []

        for blocknum, block in enumerate(page.blocks):
            fonts = []
            block_lines = []
            block_spans = []
            for linenum, line in enumerate(block.lines):
                line_text = ""
                if len(line.spans) == 0:
                    continue

                fonts = []
                line_fonts = []
                line_font_sizes = []
                line_font_weights = []


                line_text = get_line_text(line)
                block_spans.extend(line.spans)
                
                # for i, span in enumerate(line.spans):
                #     font = span.font.lower()
                #     # next_span = None
                #     # next_idx = 1
                #     # while len(line.spans) > i + next_idx:
                #     #     next_span = line.spans[i + next_idx]
                #     #     next_idx += 1
                #     #     if len(next_span.text.strip()) > 2:
                #     #         break

                #     fonts.append(font)
                #     span_text = span.text
                #     block_spans.append(span)

                    # if pagenum == 0:
                    #     print("--------", line.bbox)
                    #     print(span.chars)
                    # # Don't bold or italicize very short sequences
                    # # Avoid bolding first and last sequence so lines can be joined properly
                    # # if len(span_text) > 3 and 0 < i < len(line.spans) - 1:
                    # #     if span.italic and (not next_span or not next_span.italic):
                    # #         span_text = surround_text(span_text, "*")
                    # #     elif span.bold and (not next_span or not next_span.bold):
                    # #         span_text = surround_text(span_text, "**")
                    
                    # if line_text and span_text:
                    #     if is_chinese_character(span_text.replace("\n", "")[0]) and \
                    #         is_chinese_character(line_text.replace("\n", "")[-1]):
                            
                    #         line_text = line_text.replace("\n", "") + span_text
                    #     else:
                    #         line_text = line_text.replace("\n", "") + " " + span_text

                    # else:
                    #     line_text += span_text.replace("\n", " ")
            
                
                block_lines.append(MergedLine(
                    text=line_text,
                    fonts=[span.font.lower() for span in line.spans],
                    bbox=line.bbox, 
                ))
                
            if len(block_lines) > 0:
                page_blocks.append(MergedBlock(
                    lines=block_lines,
                    pnum=block.pnum,
                    bbox=block.bbox,
                    block_type=block.block_type,
                    html_code=block.html_code,
                    spans=block_spans
                ))
        merged_blocks.append(page_blocks)

    return merged_blocks


def block_surround(text, block_type):
    """block surround"""
    if block_type == "Section-header":
        if not text.startswith("#"):
            text = "\n## " + text.strip().title() + "\n"
    elif block_type == "Title":
        if not text.startswith("#"):
            text = "# " + text.strip().title() + "\n"
    elif block_type == "Table":
        text = "\n" + text + "\n"
    elif block_type == "List-item":
        text = escape_markdown(text)
    elif block_type == "Code":
        text = "\n```\n" + text + "\n```\n"
    elif block_type == "Text":
        text = escape_markdown(text)
    elif block_type == "Formula":
        if text.strip().startswith("$$") and text.strip().endswith("$$"):
            text = text.strip()
            text = "\n" + text + "\n"
    return text


def line_separator(line1, line2, block_type):
    """line separator"""
    # Should cover latin-derived languages and russian
    lowercase_letters = r'\p{Lo}|\p{Ll}|\d'
    hyphens = r'-—¬'
    # Remove hyphen in current line if next line and current line appear to be joined
    hyphen_pattern = regex.compile(rf'.*[{lowercase_letters}][{hyphens}]\s?$', regex.DOTALL)
    if line1 and hyphen_pattern.match(line1) and regex.match(rf"^\s?[{lowercase_letters}]", line2):
        # Split on — or - from the right
        line1 = regex.split(rf"[{hyphens}]\s?$", line1)[0]
        return line1.rstrip() + line2.lstrip()

    all_letters = r'\p{L}|\d'
    sentence_continuations = r',;\(\—\"\'\*'
    sentence_ends = r'。ๆ\.?!'
    line_end_pattern = regex.compile(rf'.*[{lowercase_letters}][{sentence_continuations}]?\s?$', regex.DOTALL)
    line_start_pattern = regex.compile(rf'^\s?[{all_letters}]', regex.DOTALL)
    sentence_end_pattern = regex.compile(rf'.*[{sentence_ends}]\s?$', regex.DOTALL)

    text_blocks = ["text", "footnote", "text_tile", "table_title", "figure_title"]
    if line1.replace("\n", "") and line2.replace("\n", "") and \
        is_chinese_character(line1.replace("\n", "")[-1]) and \
        is_chinese_character(line2.replace("\n", "")[0]) and text_blocks != "table":
        return line1.rstrip() + line2.lstrip()

    elif block_type in ["Title", "Section-header"]:
        return line1.rstrip() + " " + line2.lstrip()

    elif line_end_pattern.match(line1) and line_start_pattern.match(line2):
        return line1.rstrip() + " " + line2.lstrip()
    elif block_type in text_blocks and sentence_end_pattern.match(line1):
        return line1 + " " + line2
    elif block_type == "Table":
        return line1 + "\n\n" + line2
    else:
        return line1 + " " + line2

def sentence_end(block_text):
    """sentence end"""
    sentence_ends = r'。ๆ\.?!？!！'
    sentence_end_pattern = regex.compile(rf'.*[{sentence_ends}]\s?$', regex.DOTALL)
    if sentence_end_pattern.match(block_text):
        return True
    else:
        return False


def title_start(block_text):
    """title start"""
    start_pattern_sign = r"^([①②③④⑤⑥⑦⑧⑨⑩]|\(\d\)).+"
    if re.search(start_pattern_sign, block_text):
        return True
    else:
        return False


def block_separator(line1, line2, block_type1, block_type2):
    """block separator"""
    sep = "\n"
    if block_type1 == "Text":
        sep = "\n\n"

    return sep + line2


def samilar_text_height(element, block):
    """
    为了进行粘连，判断两个需要粘连的text 高度是不是相似
    """
    element_last_bbox = element.lines[-1].bbox
    block_first_bbox = block.lines[0].bbox
    
    el_height = element_last_bbox[3] - element_last_bbox[1]
    bl_height = block_first_bbox[3] - block_first_bbox[1]

    if el_height == 0 and len(element.lines) >= 2:
        element_last_bbox = element.lines[-2].bbox
        el_height = element_last_bbox[3] - element_last_bbox[1]

    max_height = max(el_height, bl_height)
    min_height = min(el_height, bl_height)

    right_distance = 0
    if len(element.lines) >= 2:
        above_right = element.lines[-2].bbox[2]
        bellow_right = element.lines[-1].bbox[2]
        right_distance = above_right - bellow_right

    ratio = (max_height - min_height) / (max_height + 0.0001)

    if len(element.spans) >= 2:

        el_font_weight = element.spans[-1].font_weight if element.spans[-1].text.strip() \
                                        else element.spans[-2].font_weight

    else:
        el_font_weight = True
        
    return ratio < 0.3 and abs(right_distance) < 2 * bl_height and \
                    el_font_weight == block.spans[0].font_weight


def merge_lines(pages: List[List[MergedBlock]]) -> PDFStructure:
    """mrege lines"""
    structure = PDFStructure()
    prev_block_type = None
    
    block_type = ""
    prev_informative_block_text = ""
    prev_informative_block_id = 0
    prev_block = None
    
    for page_id, page in enumerate(pages):
        for block_id, block in enumerate(page):
            block_type = block.block_type


            # for footer header
            if block_type != AttrNorm.PARA.value:
                if block_type == AttrNorm.TABLE.value and block.html_code and cfg.SHOULD_PARSE_TABLE:
                    element = Element(text=block.html_code, pos=block.bbox,
                                      attr=block_type, para_id=block_id, page_id=page_id,
                                      table_trust=block.table_trust, lines=block.lines, spans=block.spans)
                    structure.add(element)

                elif block_type == AttrNorm.FIGURE.value:
                    element = Element(text="", pos=block.bbox,
                                      attr=block_type, para_id=block_id, page_id=page_id, lines=block.lines, 
                                       spans=block.spans)
                    structure.add(element)

                else:
                    non_para_block_text = ""
                    for i, line in enumerate(block.lines):
                        if non_para_block_text:
                            non_para_block_text = line_separator(non_para_block_text, line.text, block_type)
                        else:
                            non_para_block_text = line.text
                    element = Element(text=escape_markdown(non_para_block_text), pos=block.bbox,
                                    attr=block_type, para_id=block_id, page_id=page_id, lines=block.lines,
                                     spans=block.spans)
                    structure.add(element)

        
            else:
            
                # Join lines in the block together properly
                informative_block_text = ""
                for i, line in enumerate(block.lines):
                    if informative_block_text:
                        informative_block_text = line_separator(informative_block_text, line.text, block_type)
                    else:
                        informative_block_text = line.text
                if not prev_block:
                    element = Element(text=escape_markdown(informative_block_text), pos=block.bbox,
                                     attr=block_type, para_id=block_id, page_id=page_id, lines=block.lines,
                                      spans=block.spans)
                    structure.add(element)

                elif block.pnum == prev_block.pnum and prev_block.bbox[1] < block.bbox[1] - 10:
                    element = Element(text=escape_markdown(informative_block_text), pos=block.bbox,
                                     attr=block_type, para_id=block_id, page_id=page_id, lines=block.lines,
                                      spans=block.spans)
                    structure.add(element)

                else:

                    if sentence_end(prev_informative_block_text) or \
                            prev_block_type in [AttrNorm.FIRST_LEVEL_TITLE.value, 
                                                    AttrNorm.SECOND_LEVEL_TITLE.value] or \
                                title_start(informative_block_text) or \
                                not samilar_text_height(structure[prev_informative_block_id], block):

                        element = Element(text=escape_markdown(informative_block_text), pos=block.bbox,
                                            attr=block_type, para_id=block_id, page_id=page_id, lines=block.lines,
                                             spans=block.spans)

                        structure.add(element)
                    else:
                        
                        structure[prev_informative_block_id].text = line_separator(prev_informative_block_text, 
                                                                              informative_block_text, block_type)
                        structure[prev_informative_block_id].lines.extend(block.lines)
                        structure[prev_informative_block_id].spans.extend(block.spans)
                        informative_block_text = structure[prev_informative_block_id].text
                        element = structure[prev_informative_block_id]

                prev_informative_block_text = informative_block_text
                prev_informative_block_id = element.global_index
                prev_block = block

            prev_block_type = block_type
    structure.num_pages = len(pages)
    return structure


