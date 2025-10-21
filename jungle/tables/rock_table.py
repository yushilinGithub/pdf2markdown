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

from bs4 import BeautifulSoup
from typing import List
from src.jungle.schema.page import Page
from src.jungle.schema.bbox import merge_boxes, box_intersection_pct, rescale_bbox
from src.jungle.structure import AttrNorm
from src.jungle.schema.merged import MergedLine
from PIL import ImageDraw
from loguru import logger


inter_threshold = 0.2


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


def get_cell_box(table):
    """
    convert table to bbox
    """   
    # get number rows and number columns
    htmltable = "".join(table)
    soup = BeautifulSoup(htmltable, 'html.parser')
    number_row = 0
    cells = []
    # generate an empty table
    current_row = 0
    current_col = 0
    rows = soup.find_all('tr')
    max_col = 0
    for row in rows:
        num_col = 0
        for cell in row.find_all(["td", "th"]):
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1)) 
            num_col += colspan
        if num_col > max_col:
            max_col = num_col
    row_count = 0
    cell_pos = [[{"taken" : False} for _ in range(max_col)] for _ in range(len(rows))]
    lookup_table = [[None for _ in range(max_col)] for _ in range(len(rows))]

    for row in rows:
        col_count = 0
        row_cell = [td for td in row.find_all(["td", "th"]) if td.get_text(strip=True)]
        for cell in row.find_all(["td", "th"]):
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            while col_count < len(cell_pos[row_count]) and cell_pos[row_count][col_count]["taken"] is True:
                col_count += 1

            for r in range(rowspan):
                for c in range(colspan):
                    if r == 0 and c == 0:
                        if cell.get_text(strip=True):
                            cell_pos[row_count][col_count] = {"taken" : False, "colspan" : colspan, "rowspan" : rowspan}
                        else:
                            cell_pos[row_count][col_count] = {"taken" : True, "colspan" : colspan, "rowspan" : rowspan}
#lookup_table[row_count][col_count] = [(row_count, col_count, row_count + rowspan, col_count + colspan), ()]
                    elif row_count + r < len(cell_pos):
                        cell_pos[row_count + r][col_count + c] = {"taken" : True,
                                                                     "colspan" : colspan, 
                                                                            "rowspan" : rowspan}
    #lookup_table[row_count + r][col_count + c] = [(row_count, col_count, row_count + rowspan, col_count + colspan), ()]

            col_count += 1
        row_count += 1

    result = []

    for r, row in enumerate(cell_pos):
    
        for c, col in enumerate(row):
            if col and "rowspan" in col and "colspan" in col:
                if not col["taken"]:
                    result.append((r, c, r + col["rowspan"], c + col["colspan"]))
                
                lookup_table[r][c] = [(r, c, r + col["rowspan"], c + col["colspan"]), ()]

    return result, lookup_table


def line_intersection(line1, line2):
    """ line intersection """
    min_x = min(line1[0], line2[0])
    max_x = max(line1[1], line2[1])

    min_length = min((line2[1] - line2[0]), (line1[1] - line1[0]))
    inter = min(line1[1], line2[1]) - max(line1[0], line2[0])

    return inter / min_length


def get_above_cell_horizontal(lookup_table, structure_pos, cell=None):
    """
    如果有相同 colspan 的就返回相同 colspan 的，没有就返回最接近 colspan 的。
    """

    y0, x0, y1, x1 = structure_pos

    for r in range(y0 - 1, -1, -1):
        # for sc in lookup_table[r]:
        #     structure_pos, cell_pos = sc
        #     if structure_pos[1] == x0 and structure_pos[3] == x1 and cell_pos:
        #         return (cell_pos[0], cell_pos[2])
        if  lookup_table[r][x0]:
            candidate_above_cell, cell_pos = lookup_table[r][x0]
            if cell_pos and candidate_above_cell[3] == x1 and candidate_above_cell[1] == x0:
                return (cell_pos[0], cell_pos[2])
        

def get_right_cell_vertical(lookup_table, structure_pos, cell=None):
    """
    get_right_cell_vertical
    """
    y0, x0, y1, x1 = structure_pos
    for c in range(x0 - 1, -1, -1):
        if lookup_table[y0][c]:
            candidate_right_cell, cell_pos = lookup_table[y0][c]
            if cell_pos and candidate_right_cell[2] == y1 and candidate_right_cell[0] == y0:
                return (cell_pos[1], cell_pos[3])


def check_matched(lookup_table, structure_pos, cell_pos):
    """
    check if structure_pos is in right pos
    """
    
    s_y0, s_x0, s_y1, s_x1 = structure_pos
    c_x0, c_y0, c_x1, c_y1 = cell_pos
    matched = False

    above_cell_horizontal = get_above_cell_horizontal(lookup_table, structure_pos)
    right_cell_vertical = get_right_cell_vertical(lookup_table, structure_pos)
    
    if above_cell_horizontal:
        if line_intersection(above_cell_horizontal, (c_x0, c_x1)) > inter_threshold:
            if lookup_table[s_y0][s_x0][1]:
                lc_x0, lc_y0, lc_x1, lc_y1 = lookup_table[s_y0][s_x0][1]
                if line_intersection((lc_y0, lc_y1), (c_y0, c_y1)) > inter_threshold:
                    return True
                else:
                    return False
            return True
        else:
            return False
    elif right_cell_vertical:
        if line_intersection(right_cell_vertical, (c_y0, c_y1)) > inter_threshold:
            return True
        else:
            return False
    return True


def simple_build_table_from_html_and_cell(
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


def build_table_from_html_and_cell(
    structure: List[str], content: List[str] = None
) -> List[str]:
    """Build table from html and cell token list"""

    assert structure is not None

    html_code = list()
    
    # deal with empty table
    if content is None:
        content = ["placeholder"] * len(structure)

    
    structure_bboxes, lookup_table = get_cell_box(structure)

    placeholder_tag = []
    placeholder_tag_id2tagid = {}
    
    pti = 0
    for tagid, tag in enumerate(structure):
        if tag in ("<td>[]</td>", ">[]</td>"): 
        
            placeholder_tag.append(tag)
            placeholder_tag_id2tagid[pti] = tagid
            pti += 1

    bbox_id = 0
    cell_id = 0
    give_up_matched = False
    while bbox_id < len(content) and cell_id < len(structure_bboxes):
        structure_pos = structure_bboxes[cell_id]
        s_y0, s_x0, s_y1, s_x1 = structure_pos
        
        cell = content[bbox_id]
        c_x0, c_y0, c_x1, c_y1 = cell.bbox
        structure_id = placeholder_tag_id2tagid[cell_id]

        above_cell_horizontal = get_above_cell_horizontal(lookup_table, structure_pos, cell)
        right_cell_vertical = get_right_cell_vertical(lookup_table, structure_pos, cell)

        if above_cell_horizontal:
            if line_intersection(above_cell_horizontal, (c_x0, c_x1)) > inter_threshold  \
                or (s_x0 == 0 and (above_cell_horizontal[0] + above_cell_horizontal[1]) / 2 > (c_x0 + c_x1) / 2):

                lookup_table[s_y0][s_x0][1] = cell.bbox
                #lookup_table[s_y0][s_x0].append(cell.text)
                structure_id = placeholder_tag_id2tagid[cell_id]
                structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                bbox_id += 1
                cell_id += 1
            else: # did not match
                # try match next title
                lstructure_pos = structure_bboxes[cell_id - 1]
                if cell_id + 1 < len(structure_bboxes) and check_matched(lookup_table, 
                                                                structure_bboxes[cell_id + 1], cell.bbox):
                    nstructure_pos = structure_bboxes[cell_id + 1]
                    ns_y0, ns_x0, ns_y1, ns_x1 = nstructure_pos
                    lookup_table[ns_y0][ns_x0][1] = cell.bbox
                    #lookup_table[ns_y0][ns_x0].append(cell.text)
                    structure_id = placeholder_tag_id2tagid[cell_id + 1]
                    structure[structure_id] = placeholder_tag[cell_id + 1].replace("[]", cell.text)
                    cell_id += 2
                    bbox_id += 1
                
                elif check_matched(lookup_table, lstructure_pos, cell.bbox):
                    ls_y0, ls_x0, ls_y1, ls_x1 = lstructure_pos
                    lookup_table[ls_y0][ls_x0][1] = cell.bbox
                    #lookup_table[ls_y0][ls_x0].append(cell.text)
                    structure_id = placeholder_tag_id2tagid[cell_id - 1]
                    structure[structure_id] = placeholder_tag[cell_id - 1].replace("[]", 
                                                    content[bbox_id - 1].text + cell.text)
                    bbox_id += 1
                else:
                    matched = False
                    ls_y0, ls_x0, ls_y1, ls_x1 = lstructure_pos
                    if ls_y0 < s_y0:
                        lcell_pos = lookup_table[ls_y0][ls_x0][1]
                        if line_intersection((lcell_pos[0], lcell_pos[2]), (c_y0, c_y1)) > inter_threshold:
                            ls_y0, ls_x0, ls_y1, ls_x1 = lstructure_pos
                            #lookup_table[ls_y0][ls_x0].append(cell.text)
                            structure_id = placeholder_tag_id2tagid[cell_id - 1]
                            structure[structure_id] = placeholder_tag[cell_id - 1].replace("[]", 
                                                                content[bbox_id - 1].text + cell.text)
                            bbox_id += 1
                            matched = True
                    elif ls_y0 == s_y0: #same row, in the left of next col
                        #print(cell.text, structure_pos)
                        lcell_pos = lookup_table[ls_y0][ls_x0][1]
                        if line_intersection((lcell_pos[1], lcell_pos[3]), (c_y0, c_y1)) > inter_threshold: 
                            #print("inside", cell.text, structure_pos)
                            if s_x0 + 1 < len(lookup_table[s_y0 - 1]):
                                upleftbbox = lookup_table[s_y0 - 1][s_x0 + 1][1]
                            
                                if len(upleftbbox) == 4 and (c_x0 + c_x1) / 2 < (upleftbbox[0] + upleftbbox[2]) / 2:
                                    structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                                    lookup_table[s_y0][s_x0][1] = cell.bbox
                                    bbox_id += 1
                                    cell_id += 1
                                    matched = True
                            else:
                                structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                                lookup_table[s_y0][s_x0][1] = cell.bbox
                                bbox_id += 1
                                cell_id += 1
                                matched = True
                    if not matched:
                        structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                        lookup_table[s_y0][s_x0][1] = cell.bbox
                        bbox_id += 1
                        cell_id += 1
                        #print("give up matched above", cell.text, structure_pos)
                        give_up_matched = True

                # try match last title

        elif right_cell_vertical:
            if line_intersection(right_cell_vertical, (c_y0, c_y1)) > inter_threshold:
                structure_id = placeholder_tag_id2tagid[cell_id]
                structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                lookup_table[s_y0][s_x0][1] = cell.bbox
                #lookup_table[s_y0][s_x0].append(cell.text)
                bbox_id += 1
                cell_id += 1
            else: # did not match
                                # try match next title
                
                lstructure_pos = structure_bboxes[cell_id - 1]
                if cell_id + 1 < len(structure_bboxes) and check_matched(lookup_table, 
                                                structure_bboxes[cell_id + 1], cell.bbox):
                    nstructure_pos = structure_bboxes[cell_id + 1]
                    ns_y0, ns_x0, ns_y1, ns_x1 = nstructure_pos
                    lookup_table[ns_y0][ns_x0][1] = cell.bbox
                    #lookup_table[ns_y0][ns_x0].append(cell.text)
                    structure_id = placeholder_tag_id2tagid[cell_id + 1]
                    structure[structure_id] = placeholder_tag[cell_id + 1].replace("[]", cell.text)
                    cell_id += 2
                    bbox_id += 1
                elif check_matched(lookup_table, lstructure_pos, cell.bbox):
                    ls_y0, ls_x0, ls_y1, ls_x1 = lstructure_pos
                    lookup_table[ls_y0][ls_x0][1] = cell.bbox
                    #lookup_table[ls_y0][ls_x0].append(cell.text)
                    structure_id = placeholder_tag_id2tagid[cell_id - 1]
                    structure[structure_id] = placeholder_tag[cell_id - 1].replace("[]",
                                                 content[bbox_id - 1].text + cell.text)
                    bbox_id += 1
                else:
                    structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
                    #lookup_table[s_y0][s_x0].append(cell.text)
                    lookup_table[s_y0][s_x0][1] = cell.bbox
                    #lookup_table[s_y0][s_x0].append(cell.text)
                    #print("give up matched right", cell.text, structure_pos)
                    give_up_matched = True
                    bbox_id += 1
                    cell_id += 1
        else:
            structure_id = placeholder_tag_id2tagid[cell_id]
            structure[structure_id] = placeholder_tag[cell_id].replace("[]", cell.text)
            lookup_table[s_y0][s_x0][1] = cell.bbox
            #lookup_table[s_y0][s_x0].append(cell.text)
            bbox_id += 1
            cell_id += 1
    
    result_structure = []
    for cid, tag in enumerate(structure):
        if tag in ("<td>[]</td>", ">[]</td>"): 
            if cid <= cell_id:
                result_structure.append(tag.replace("[]", ""))
            else:
                continue
        else:
            result_structure.append(tag)
    #print("result_sturcture", result_structure)

    return give_up_matched, result_structure


def get_block_rotation(block):
    """
    get rotation for a single block
    """ 
    text_length = 0
    rotation_dict = {}
    for text_line in block.lines:
        for span in text_line.spans:
            if span.text:
                if int(span.rotation) in rotation_dict:
                    rotation_dict[int(span.rotation)] += len(span.text)
                else:
                    rotation_dict[int(span.rotation)] = 0

    if rotation_dict:
        rotation = max(rotation_dict, key=rotation_dict.get)
    else:
        rotation = 0
    return rotation


def rotate_bbox(bbox, angle, image_size):
    """Rotate a bounding box given the rotation angle."""
    width, height = image_size
    # Create a rotation matrix
    if angle == 90:
        return (height - bbox[3], bbox[0], height - bbox[1], bbox[2])  # Adjusted for 90 degrees
    elif angle == 180:
        return (width - bbox[2], height - bbox[3], width - bbox[0], height - bbox[1])  # Adjusted for 180 degrees
    elif angle == 270:
        return (bbox[1], width - bbox[2], bbox[3], width - bbox[0])  # Adjusted for 270 degrees
    return bbox


def format_tables(pages: List[Page], table_model):
    """# Formats tables nicely into github flavored markdown"""
    table_count = 0
    table_images = []
    bboxes = []

    table_blocks = []
    table_pages_id = []
    rotations = []

    for page_id, page in enumerate(pages):
        table_insert_points = {}
        blocks_to_remove = set()
        pnum = page.pnum

        for block_id, block in enumerate(page.blocks):
            if block.block_type == AttrNorm.TABLE.value:
                bbox = block.bbox
                image = page.page_image
                table_image = image.crop(bbox)
                bboxes.append(bbox)
                table_blocks.append(block)
                table_rotation = get_block_rotation(block)

                if table_rotation != 0:
                    table_image = table_image.rotate(table_rotation - 360, expand=True)    
                    # import uuid
                    # print("save image")
                    # table_image.save(f"{uuid.uuid4()}.jpg")
                rotations.append(table_rotation)
                table_images.append(table_image)
                table_pages_id.append((page_id, block_id))

    if len(table_images) > 0:
        result_bboxes, result_structures = table_model(table_images)
        
        # find lines belongs to table cell
        for bbox, cell_bboxes, result_structure, table_block, pb_id, rotation, table_image in zip(bboxes, 
                                                                            result_bboxes, 
                                                                            result_structures, 
                                                                            table_blocks, 
                                                                            table_pages_id,
                                                                            rotations,
                                                                            table_images):
            page_id, block_id = pb_id
            table_page = pages[page_id]
            bx0, by0, bx1, by1 = bbox
            # get cell content
            image = table_page.page_image
            #draw = ImageDraw.Draw(image)
            cell_contents = []

            
            for cell_bbox in cell_bboxes:
                
                if rotation != 0:
                    cell_bbox = rotate_bbox(cell_bbox, rotation, (table_image.width, table_image.height))

                projected_cell_bbox = cell_bbox[0] + bx0, cell_bbox[1] + by0, cell_bbox[2] + bx0, cell_bbox[3] + by0
                
                #draw.rectangle(projected_cell_bbox, outline="red")
                cell_chars = []
                cell_spans = []
                for text_line in table_block.lines:
                    for span in text_line.spans:
                        rescaled_span_bbox = rescale_bbox(table_page.bbox, table_page.layout.image_bbox, span.bbox)
                        if span.chars:
                            for char in span.chars:                          
                                rescaled_char_bbox = rescale_bbox(table_page.bbox, 
                                                        table_page.layout.image_bbox, char["bbox"])
                                intersect_pct = box_intersection_pct(rescaled_char_bbox, projected_cell_bbox)
                                #draw.rectangle(rescaled_char_bbox, outline="green")
                                if intersect_pct >= 0.3:
                                    cell_chars.append(char)

                        else:
                            rescaled_span_bbox = rescale_bbox(table_page.bbox, table_page.layout.image_bbox, span.bbox)

                            #draw.rectangle(rescaled_span_bbox, outline="green")
                            intersect_pct = box_intersection_pct(rescaled_span_bbox, projected_cell_bbox)
                            if intersect_pct >= 0.3:
                                cell_spans.append(span)
  
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
                                            bbox=bbox,
                                            #table_cell_bbox=bbox,
                                        )
                cell_contents.append(cell_content)
            #image.save(f"{page_id}_{block_id}.jpg")   
            try:
                #if rotation == 0:
                give_up_matched, html_code = build_table_from_html_and_cell(result_structure, cell_contents)
                html_code = "".join(html_code)
                html_code = html_table_template(html_code)
                table_block.html_code = html_code
                table_block.table_trust = not give_up_matched

                # else:
                #     html_code = simple_build_table_from_html_and_cell(result_structure, cell_contents)
                #     html_code = "".join(html_code)
                #     html_code = html_table_template(html_code)
                #     table_block.html_code = html_code
                #     table_block.table_trust = True

            except Exception as e:
                logger.error(f"table match false {e}")
                html_code = simple_build_table_from_html_and_cell(result_structure, cell_contents)
                html_code = "".join(html_code)
                html_code = html_table_template(html_code)
                table_block.html_code = html_code
                table_block.table_trust = False
            pages[page_id].blocks[block_id] = table_block
    return pages           
            
            