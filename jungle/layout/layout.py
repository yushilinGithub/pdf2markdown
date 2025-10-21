#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
layout.

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from typing import List

from src.rock.layout import batch_layout_detection

from src.jungle.pdf.images import render_image
from src.jungle.schema.bbox import rescale_bbox, box_intersection_pct
from src.jungle.schema.page import Page
from src.jungle.settings import settings
from src.jungle.schema.block import Block
from PIL import ImageDraw

from src.rock.layout import batch_layout_detection


def get_batch_size():
    """get batch size"""
    if settings.LAYOUT_BATCH_SIZE is not None:
        return settings.LAYOUT_BATCH_SIZE
    elif settings.TORCH_DEVICE_MODEL == "cuda":
        return 6
    return 6


def layout1(doc, pages: List[Page], layout_predictor, batch_multiplier=6):
    """layout prediction"""
    #images = [render_image(doc[pnum], dpi=settings.SURYA_LAYOUT_DPI) for pnum in range(len(pages))]
    images = [page.page_image for page in pages]

    layout_predictions = batch_layout_detection(images, layout_predictor, batch_size=settings.LAYOUT_BATCH_SIZE)
    page_idxs = [idx for idx in range(len(pages))]

    for page_idx, page, layout_prediction in zip(page_idxs, pages, layout_predictions):
        page.layout = layout_prediction

        blocks = []
        for i, layout_instance in enumerate(layout_prediction.bboxes):

            lines = []
            for block in page.blocks:
                for line in block.lines:

                    line_bbox = rescale_bbox(page.bbox, page.layout.image_bbox, line.bbox)
                    if box_intersection_pct(line_bbox, layout_instance.bbox) > 0.5:
                        lines.append(line)


            block = Block(
                bbox=layout_instance.bbox,
                pnum=page_idx,
                lines=lines,
                block_type=layout_instance.label
            )
            blocks.append(block)
        page.blocks = blocks


def layout(doc, pages: List[Page], layout_predictor, batch_multiplier=6):
    """layout prediction and two round matching, return a mean intersection_pct of all pages"""
    #images = [render_image(doc[pnum], dpi=settings.SURYA_LAYOUT_DPI) for pnum in range(len(pages))]
    images = [page.page_image for page in pages]

    layout_predictions = batch_layout_detection(images, layout_predictor, batch_size=settings.LAYOUT_BATCH_SIZE)
    page_idxs = [idx for idx in range(len(pages))]

    pdf_intersection_pct_sum = 0
    pdf_pct_num_page_encountered = 0
    for page_idx, page, layout_prediction in zip(page_idxs, pages, layout_predictions):
        page.layout = layout_prediction

        lines2layout = {}
        lines = []

        # drawing_image = page.page_image.copy()
        # drawing = ImageDraw.Draw(drawing_image)
        for block in page.blocks:
            for line in block.lines:
                line_max_interception_pct_layout = None
                line_max_intersection_pct = 0
                line_bbox = rescale_bbox(page.bbox, page.layout.image_bbox, line.bbox)
                #drawing.rectangle(line_bbox, outline="blue")
                for layout_id, layout_instance in enumerate(layout_prediction.bboxes):
            
                    intersection_pct = box_intersection_pct(line_bbox, layout_instance.bbox)


                    if intersection_pct > line_max_intersection_pct:
                        line_max_interception_pct_layout = layout_id
                        line_max_intersection_pct = intersection_pct

                lines2layout[len(lines)] = (line_max_interception_pct_layout, line_max_intersection_pct)
                lines.append(line)

        # compute the pdf mean intersection pct
        page_intersection_pct_sum = 0
        num_intersections_encountered = 0
        for line_id, line in enumerate(lines):
            _, interception_pct = lines2layout[line_id]
            if interception_pct > 0:
                page_intersection_pct_sum += interception_pct
                num_intersections_encountered += 1
        
        page_intersection_pct_mean = page_intersection_pct_sum / num_intersections_encountered \
                                    if num_intersections_encountered > 0 else 0
        pdf_intersection_pct_sum += page_intersection_pct_mean
        if page_intersection_pct_mean != 0:
            pdf_pct_num_page_encountered = pdf_pct_num_page_encountered + 1
                
        blocks = []

        for layout_id, layout_instance in enumerate(layout_prediction.bboxes):
            #drawing.rectangle(layout_instance.bbox, outline="red")

            blocked_lines = []
            for line_id, line in  enumerate(lines):
                
                bbox_id, box_intersection = lines2layout[line_id]
                if bbox_id == layout_id and box_intersection > 0:
                    blocked_lines.append(line)

            block = Block(
                bbox=layout_instance.bbox,
                pnum=page_idx,
                lines=blocked_lines,
                block_type=layout_instance.label
            )
            blocks.append(block)
        #drawing_image.save(f"{page_idx}.png")
        page.blocks = blocks
    
    return pdf_intersection_pct_sum / (pdf_pct_num_page_encountered + 0.0001)
    
def annotate_block_types(pages: List[Page]):
    """annotate block types"""
    for page in pages:
        max_intersections = {}
        for i, block in enumerate(page.blocks):
            for j, layout_block in enumerate(page.layout.bboxes):
                layout_bbox = layout_block.bbox
                layout_bbox = rescale_bbox(page.layout.image_bbox, page.bbox, layout_bbox)
                intersection_pct = block.intersection_pct(layout_bbox)
                if i not in max_intersections:
                    max_intersections[i] = (intersection_pct, j)
                elif intersection_pct > max_intersections[i][0]:
                    max_intersections[i] = (intersection_pct, j)

        for i, block in enumerate(page.blocks):
            block = page.blocks[i]
            block_type = "Text"
            if i in max_intersections:
                j = max_intersections[i][1]
                block_type = page.layout.bboxes[j].label
            block.block_type = block_type


