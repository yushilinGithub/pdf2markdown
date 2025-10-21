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

from typing import List
from src.jungle.schema.page import Page
from src.jungle.schema.bbox import merge_boxes, box_intersection_pct, rescale_bbox
from src.jungle.schema.merged import MergedLine
from PIL import ImageDraw


html_table_template = (
    lambda table: f"""<html>
        <head> <meta charset="UTF-8">
        <style>
        table, th, td {{
            border: 1px solid black;
            font-size: 10px;
        }}
        </style> </head>
        <body>
        <table frame="hsides" rules="groups" width="100%%">
            {table}
        </table> </body> </html>"""
)


def build_table_from_html_and_cell(
    structure: List[str], content: List[str] = None
) -> List[str]:
    """Build table from html and cell token list"""
    assert structure is not None
    html_code = list()

    # deal with empty table
    if content is None:
        content = ["placeholder"] * len(structure)

    for tag in structure:
        if tag in ("<td>[]</td>", ">[]</td>"):
            if len(content) == 0:
                continue
            cell = content.pop(0)
            html_code.append(tag.replace("[]", cell.text))
        else:
            html_code.append(tag)

    return html_code


def format_tables(pages: List[Page], table_model):
    """# Formats tables nicely into github flavored markdown"""
    table_count = 0
    table_images = []
    bboxes = []

    table_blocks = []
    table_pages_id = []

    for page_id, page in enumerate(pages):
        table_insert_points = {}
        blocks_to_remove = set()
        pnum = page.pnum

        for block_id, block in enumerate(page.blocks):
            if block.block_type == "table":
                bbox = block.bbox
                image = page.page_image
                table_image = image.crop(bbox)
                bboxes.append(bbox)
                table_blocks.append(block)
                table_images.append(table_image)
                table_pages_id.append((page_id, block_id))
    if len(table_images) > 0:
        result_bboxes, result_structures = table_model(table_images)
        # find lines belongs to table cell
        for bbox, cell_bboxes, result_structure, table_block, pb_id in zip(bboxes, 
                                                                            result_bboxes, 
                                                                            result_structures, 
                                                                            table_blocks, 
                                                                            table_pages_id):
            page_id, block_id = pb_id
            table_page = pages[page_id]
            bx0, by0, bx1, by1 = bbox
            # get cell content
            image = table_page.page_image
            #draw = ImageDraw.Draw(image)
            cell_contents = []
            for cell_bbox in cell_bboxes:
                projected_cell_bbox = cell_bbox[0] + bx0, cell_bbox[1] + by0, cell_bbox[2] + bx0, cell_bbox[3] + by0
                #draw.rectangle(projected_cell_bbox, outline="red")
                cell_chars = []
                cell_spans = []
                for text_line in table_block.lines:
                    for span in text_line.spans:
                        if span.chars:
                            for char in span.chars:                           
                                rescaled_char_bbox = rescale_bbox(table_page.bbox, table_page.layout.image_bbox, char["bbox"])
                                intersect_pct = box_intersection_pct(rescaled_char_bbox, projected_cell_bbox)
                                if intersect_pct >= 0.5:
                                    cell_chars.append(char)
                        else:
                            rescaled_span_bbox = rescale_bbox(table_page.bbox, table_page.layout.image_bbox, span.bbox)

                            #draw.rectangle(rescaled_span_bbox, outline="blue")
                            intersect_pct = box_intersection_pct(rescaled_span_bbox, projected_cell_bbox)
                            if intersect_pct >= 0.5:
                                cell_spans.append(span)
                #image.save(f"{page_id}_{block_id}.jpg")   
                cell_text = ""
                # if len(cell_spans) == 0:
                #     continue
                fonts = []
                if cell_chars:
                    for i, char in enumerate(cell_chars):
                        cell_text += char["char"]
                elif cell_spans:                    
                    for span in cell_spans:
                        cell_text += span.text

                cell_content = MergedLine(
                                            text=cell_text,
                                            fonts=fonts,
                                            bbox=projected_cell_bbox
                                        )
                cell_contents.append(cell_content)
            #image.save(f"{page_id}_{block_id}.jpg")   
            html_code = build_table_from_html_and_cell(result_structure, cell_contents)
            html_code = "".join(html_code)
            html_code = html_table_template(html_code)
            table_block.html_code = html_code
            pages[page_id].blocks[block_id] = table_block
    return pages           
            
            