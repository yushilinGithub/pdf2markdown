#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
convert list of elements to tree.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""
from src.jungle.structure.attr_norm import AttrNorm



def build_tree(elements):
    """
    build tree from 
    """
    tree = []
    stack = []

    for element in elements:
        if element.meta_name is not None:
            continue

        if element.title_level != -1:
            # Create a new title node
            if not element.inline_title_extracted:
                node = {
                    'type': 'title',
                    'id': element.id,
                    'text': element.text,
                    'elements': []
                }
            else:
                node = {
                    'type': 'title',
                    'id': element.id,
                    'text': element.text.split("\n\n")[0],
                    'elements': [{
                                    'type': 'para',
                                    'id': element.id,
                                    'text': element.text.split("\n\n")[1],
                                    'corresponding_medium': element.corresponding_medium
                                }]
                }
            # Manage stack based on title_level
            while stack and stack[-1]['level'] >= element.title_level:
                stack.pop()
            if stack:
                stack[-1]['node']['elements'].append(node)
            else:
                tree.append(node)
            stack.append({'node': node, 'level': element.title_level})
        elif element.title_level == -1 and element.attr == AttrNorm.PARA.value:
            # Create a new paragraph node
            para_node = {
                'type': 'para',
                'id': element.id,
                'text': element.text,
                'corresponding_medium': element.corresponding_medium
            }
            if stack:
                stack[-1]['node']['elements'].append(para_node)
        elif element.attr == AttrNorm.TABLE.value:
            # Create a new figure node
            table_node = {
                'type': 'table',
                'id': element.id,
                'table_title': element.table_title,
                "table_html": element.text,
                'table_footnote': element.table_footnote,
                'table_figure_url': element.table_figure_url,
                'table_trust': element.table_trust
            }
            if stack:
                stack[-1]['node']['elements'].append(table_node)
        elif element.attr == "figure":
            # Create a new figure node
            figure_node = {
                'type': 'figure',
                'id': element.id,
                'figure_title': element.figure_title,
                'figure_caption': element.figure_caption,
                'figure_url': element.figure_url,
                'figure_footnote': element.figure_footnote,
            }
            if stack:
                stack[-1]['node']['elements'].append(figure_node)
    
    return tree


    

