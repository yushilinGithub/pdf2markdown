#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
match figure title with figure content, table title and table content.
match table title with corresponding paragraph content. 

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


from scipy.optimize import linear_sum_assignment
from src.jungle.structure.attr_norm import AttrNorm
import math
import re
from loguru import logger


def match_table(structure):
    """
    match table title with corresponding paragraph content.
    """
    page_table = {}
    page_table_title = {}

    for element in structure:
        if element.attr == AttrNorm.TABLE.value:
            if element.page_id not in page_table:
                page_table[element.page_id] = [element]
            else:
                page_table[element.page_id].append(element)
        elif element.attr == AttrNorm.TABLE_TITLE.value:
            if element.page_id not in page_table_title:
                page_table_title[element.page_id] = [element]
            else:
                page_table_title[element.page_id].append(element)

    for page_id, tables in page_table.items():
        if page_id not in page_table_title:
            continue
        elif len(tables) == 1 and len(page_table_title[page_id]) == 1:
            tables[0].table_title = page_table_title[page_id][0].text

        elif len(page_table_title[page_id]) == 0:
            continue

        else:

            page_matrix = [[0 for _ in range(len(page_table_title[page_id]))] 
                                for _ in range(len(tables))]
            for tid, table in enumerate(tables):
                for ttid, table_title in enumerate(page_table_title[page_id]):
                    table_bottom_center = ((table.pos[0] + table.pos[2]) / 2, table.pos[3])
                    table_title_center = ((table_title.pos[0] + table_title.pos[2]) / 2, 
                                        (table_title.pos[1] + table_title.pos[3]) / 2)
                    page_matrix[tid][ttid] = math.hypot(table_bottom_center[0] - table_title_center[0], 
                                                            table_bottom_center[1] - table_title_center[1])
        
            row_ind, col_ind = linear_sum_assignment(page_matrix)

            for i, ci in enumerate(col_ind):
                tables[row_ind[i]].table_title = page_table_title[page_id][ci].text
    
    return structure


def table_association(structure):
    """
    table association
    """
    table_id_pattern = r'(TABLE|Table|表)\s?(\d+(?:-\d+)*)'
    for eid, element in enumerate(structure):
        if element.attr == AttrNorm.TABLE.value and element.table_title:
            table_title_id_match = re.search(table_id_pattern, element.table_title)
            if table_title_id_match:
                table_title_id = table_title_id_match.group()
            else:
                logger.warning(f"{element.table_title} did not match any pattern")
                continue
            table_id = element.table_id
            page_id = element.page_id
            
            for back_element in structure[:eid][::-1]:
                if back_element.page_id < page_id - 1:
                    break 
                if back_element.attr == AttrNorm.PARA.value:
                    string_start = back_element.text.find(table_title_id)
                    if string_start == -1:
                        continue
                    else:
                        back_element.corresponding_medium.append({"type": "table",
                                                            "id": table_id,
                                                            "offset": string_start})

            for forward_element in structure[eid:]:
                if forward_element.page_id > page_id + 1:
                    break
            
                if forward_element.attr == AttrNorm.PARA.value:
                    string_start = forward_element.text.find(table_title_id)
                    if string_start == -1:
                        continue
                    else:
                        forward_element.corresponding_medium.append({"type": "table",
                                                                    "id": table_id,
                                                                    "offset": string_start})
                        

    return structure

                        
            
