#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
model setup script.

Authors: yushilin(yushilin@baidu.com)
Date:    2024/07/29 17:08:41
"""


from typing import List

from pydantic import BaseModel, field_validator


def should_merge_blocks(box1, box2, tol=5):
    """Within tol y px, and to the right within tol px"""
    merge = [
        box2[0] > box1[0], # After in the x coordinate
        abs(box2[1] - box1[1]) < tol, # Within tol y px
        abs(box2[3] - box1[3]) < tol, # Within tol y px
        abs(box2[0] - box1[2]) < tol, # Within tol x px
    ]
    return all(merge)


def merge_boxes(box1, box2):
    """merge boxes"""
    return (min(box1[0], box2[0]), min(box1[1], box2[1]), max(box2[2], box1[2]), max(box1[3], box2[3]))


def boxes_intersect(box1, box2):
    """Box1 intersects box2"""
    return box1[0] < box2[2] and box1[2] > box2[0] and box1[1] < box2[3] and box1[3] > box2[1]


def box_intersection_pct(box1, box2):
    """ determine the coordinates of the intersection rectangle"""
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bb1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])

    if bb1_area == 0:
    
        pin1 = box2[0] <= box1[0] <= box2[2] and  box2[1] <= box1[1] <= box2[3]
        pin2 = box2[0] <= box1[2] <= box2[2] and  box2[1] <= box1[3] <= box2[3]
        return 1
    iou = intersection_area / bb1_area
    return iou


def multiple_boxes_intersect(box1, boxes):
    """multiple boxes intersect"""
    for box2 in boxes:
        if boxes_intersect(box1, box2):
            return True
    return False


def unnormalize_box(bbox, width, height):
    """unnormalize box"""
    return [
        width * (bbox[0] / 1000),
        height * (bbox[1] / 1000),
        width * (bbox[2] / 1000),
        height * (bbox[3] / 1000),
    ]


class BboxElement(BaseModel):
    """Bbox element"""
    bbox: List[float]

    @field_validator('bbox')
    @classmethod
    def check_4_elements(cls, v: List[float]) -> List[float]:
        """check 4 element"""
        if len(v) != 4:
            raise ValueError('bbox must have 4 elements')
        return v

    @property
    def height(self):
        """height"""
        return self.bbox[3] - self.bbox[1]

    @property
    def width(self):
        """width"""
        return self.bbox[2] - self.bbox[0]

    @property
    def x_start(self):
        """x start"""
        return self.bbox[0]

    @property
    def y_start(self):
        """y_ start"""
        return self.bbox[1]

    @property
    def area(self):
        """area"""
        return self.width * self.height

    def intersection_pct(self, other_bbox: List[float]):
        """intersection pct"""
        if self.area == 0:
            return 0.0
        return box_intersection_pct(self.bbox, other_bbox)


def rescale_bbox(orig_dim, new_dim, bbox):
    """rescale bbox"""
    page_width, page_height = new_dim[2] - new_dim[0], new_dim[3] - new_dim[1]
    detected_width, detected_height = orig_dim[2] - orig_dim[0], orig_dim[3] - orig_dim[1]
    width_scaler = detected_width / page_width
    height_scaler = detected_height / page_height

    new_bbox = [bbox[0] / width_scaler, bbox[1] / height_scaler, bbox[2] / width_scaler, bbox[3] / height_scaler]
    return new_bbox
