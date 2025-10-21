#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
Setup script.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""

from itertools import chain

import sklearn

from src.pdftext.pdf.utils import LINE_BREAKS, TABS, SPACES
from src.pdftext.settings import settings


def update_current(current, new_char):
    """update"""
    bbox = new_char["bbox"]
    if "bbox" not in current:
        current["bbox"] = bbox.copy()
    else:
        current_bbox = current["bbox"]
        current_bbox[0] = min(bbox[0], current_bbox[0])
        current_bbox[1] = min(bbox[1], current_bbox[1])
        current_bbox[2] = max(bbox[2], current_bbox[2])
        current_bbox[3] = max(bbox[3], current_bbox[3])
    current_bbox = current["bbox"]
    current["center_x"] = (current_bbox[0] + current_bbox[2]) / 2
    current["center_y"] = (current_bbox[1] + current_bbox[3]) / 2


def create_training_row(char_info, prev_char, currblock, currline):
    """create training row"""
    char = char_info["char"]

    # Store variables used multiple times
    char_bbox = char_info["bbox"]
    prev_bbox = prev_char["bbox"]
    currblock_bbox = currblock["bbox"]
    currline_bbox = currline["bbox"]

    char_x1, char_y1, char_x2, char_y2 = char_bbox
    prev_x1, prev_y1, prev_x2, prev_y2 = prev_bbox
    char_center_x = (char_x2 + char_x1) / 2
    char_center_y = (char_y2 + char_y1) / 2
    x_gap = char_x1 - prev_x2
    y_gap = char_y1 - prev_y2

    char_font = char_info["font"]
    prev_font = prev_char["font"]
    font_match = (char_font["name"] == prev_font["name"] and
                  char_font["size"] == prev_font["size"] and
                  char_font["weight"] == prev_font["weight"] and
                  char_font["flags"] == prev_font["flags"] and
                  char_info["rotation"] == prev_char["rotation"])

    is_space = char in SPACES or char in TABS

    training_row = {
        "is_newline": char in LINE_BREAKS,
        "is_space": is_space,
        "x_gap": x_gap,
        "y_gap": y_gap,
        "font_match": font_match,
        "x_outer_gap": char_x2 - prev_x1,
        "y_outer_gap": char_y2 - prev_y1,
        "line_x_center_gap": char_center_x - currline["center_x"],
        "line_y_center_gap": char_center_y - currline["center_y"],
        "line_x_gap": char_x1 - currline_bbox[2],
        "line_y_gap": char_y1 - currline_bbox[3],
        "line_x_start_gap": char_x1 - currline_bbox[0],
        "line_y_start_gap": char_y1 - currline_bbox[1],
        "block_x_center_gap": char_center_x - currblock["center_x"],
        "block_y_center_gap": char_center_y - currblock["center_y"],
        "block_x_gap": char_x1 - currblock_bbox[2],
        "block_y_gap": char_y1 - currblock_bbox[3],
        "block_x_start_gap": char_x1 - currblock_bbox[0],
        "block_y_start_gap": char_y1 - currblock_bbox[1]
    }

    return training_row


def update_span(line, span):
    """update span"""
    if span["chars"]:
        first_char = span["chars"][0]
        span["font"] = first_char["font"]
        span["rotation"] = first_char["rotation"]

        char_bboxes = [char["bbox"] for char in span["chars"]]
        min_x, min_y, max_x, max_y = char_bboxes[0]

        for bbox in char_bboxes[1:]:
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

        span["bbox"] = [min_x, min_y, max_x, max_y]
        span["text"] = "".join(char["char"] for char in span["chars"])
        span["char_start_idx"] = first_char["char_idx"]
        span["char_end_idx"] = span["chars"][-1]["char_idx"]

        # Remove unneeded keys from the characters
        for char in span["chars"]:
            for key in list(char.keys()):
                if key not in ["char", "bbox"]:
                    del char[key]

        line["spans"].append(span)
    return {"chars": []}


def update_line(block, line):
    """update line"""
    block["lines"].append(line)
    line = {"spans": []}
    return line


def update_block(blocks, block):
    """update block"""
    blocks["blocks"].append(block)
    block = {"lines": []}
    return block


def infer_single_page(text_chars, block_threshold=settings.BLOCK_THRESHOLD):
    """infer single page"""
    prev_char = None
    prev_font_info = None

    blocks = {
        "blocks": [],
        "page": text_chars["page"],
        "rotation": text_chars["rotation"],
        "bbox": text_chars["bbox"],
        "width": text_chars["width"],
        "height": text_chars["height"],
    }
    block = {"lines": []}
    line = {"spans": []}
    span = {"chars": []}

    for char_info in text_chars["chars"]:
        font = char_info['font']
        font_info = f"{font['name']}_{font['size']}_{font['weight']}_{font['flags']}_{char_info['rotation']}"
        if prev_char:
            training_row = create_training_row(char_info, prev_char, block, line)
            sorted_keys = sorted(training_row.keys())
            training_row = [training_row[key] for key in sorted_keys]
            char_height = char_info["bbox"][3] - char_info["bbox"][1]
            prediction_probs = yield training_row
            # First item is probability of same line/block, second is probability of new line, third is probability of new block
            if prediction_probs[0] >= .5:
                # Ensure we update spans properly for font info when predicting no new line
                if prev_font_info != font_info:
                    span = update_span(line, span)
            elif prediction_probs[2] > block_threshold:
                span = update_span(line, span)
                line = update_line(block, line)
                block = update_block(blocks, block)
            elif prev_char["char"] in LINE_BREAKS: # Look for newline character as a forcing signal for a new line
                span = update_span(line, span)
                line = update_line(block, line)
            elif prev_char["bbox"][0] > char_info["bbox"][2]: # Look for horizontal line break as a forcing signal for a new line
                span = update_span(line, span)
                line = update_line(block, line)
            elif char_info["bbox"][0] - prev_char["bbox"][2] > char_height * 5:
                span = update_span(line, span)
                line = update_line(block, line)

            elif prev_font_info != font_info:
                span = update_span(line, span)

        span["chars"].append(char_info)
        update_current(line, char_info)
        update_current(block, char_info)

        prev_char = char_info
        prev_font_info = font_info

    if span["chars"]:
        update_span(line, span)
    if line["spans"]:
        update_line(block, line)
    if block["lines"]:
        update_block(blocks, block)

    return blocks


def inference(text_chars, model):
    """predict"""
    # Create generators and get first training row from each
    generators = [infer_single_page(text_page) for text_page in text_chars]
    next_prediction = {}

    page_blocks = {}
    while len(page_blocks) < len(generators):
        training_data = {}
        for page_idx, page_generator in enumerate(generators):
            if page_idx in page_blocks:
                continue

            try:
                if page_idx not in next_prediction:
                    training_row = next(page_generator)
                else:
                    training_row = page_generator.send(next_prediction[page_idx])
                    del next_prediction[page_idx]
                training_data[page_idx] = training_row
            except StopIteration as e:
                blocks = e.value
                page_blocks[page_idx] = blocks

        if len(page_blocks) == len(generators):
            break

        training_idxs = sorted(training_data.keys())
        training_rows = [training_data[idx] for idx in training_idxs]

        # Disable nan, etc, validation for a small speedup
        with sklearn.config_context(assume_finite=True):
            predictions = model.predict_proba(training_rows)
        for pred, page_idx in zip(predictions, training_idxs):
            next_prediction[page_idx] = pred
    sorted_keys = sorted(page_blocks.keys())
    page_blocks = [page_blocks[key] for key in sorted_keys]
    assert len(page_blocks) == len(text_chars)
    return page_blocks
