# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
text recognition。

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""


import copy
from typing import List, Tuple, Any, Optional

from pydantic import BaseModel, field_validator, computed_field

from src.rock.postprocessing.util import rescale_bbox


class PolygonBox(BaseModel):
    """polygon box"""
    polygon: List[List[float]]
    confidence: Optional[float] = None

    @field_validator('polygon')
    @classmethod
    def check_elements(cls, v: List[List[float]]) -> List[List[float]]:
        """check elements"""
        if len(v) != 4:
            raise ValueError('corner must have 4 elements')

        for corner in v:
            if len(corner) != 2:
                raise ValueError('corner must have 2 elements')
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
    def area(self):
        """area"""
        return self.width * self.height

    @computed_field
    @property
    def bbox(self) -> List[float]:
        """bbox"""
        box = [self.polygon[0][0], self.polygon[0][1], self.polygon[1][0], self.polygon[2][1]]
        if box[0] > box[2]:
            box[0], box[2] = box[2], box[0]
        if box[1] > box[3]:
            box[1], box[3] = box[3], box[1]
        return box

    def rescale(self, processor_size, image_size):
        """rescale"""
        # Point is in x, y format
        page_width, page_height = processor_size

        img_width, img_height = image_size
        width_scaler = img_width / page_width
        height_scaler = img_height / page_height

        new_corners = copy.deepcopy(self.polygon)
        for corner in new_corners:
            corner[0] = int(corner[0] * width_scaler)
            corner[1] = int(corner[1] * height_scaler)
        self.polygon = new_corners

    def fit_to_bounds(self, bounds):
        """fit to bounds"""
        new_corners = copy.deepcopy(self.polygon)
        for corner in new_corners:
            corner[0] = max(min(corner[0], bounds[2]), bounds[0])
            corner[1] = max(min(corner[1], bounds[3]), bounds[1])
        self.polygon = new_corners

    def merge(self, other):
        """merge"""
        x1 = min(self.bbox[0], other.bbox[0])
        y1 = min(self.bbox[1], other.bbox[1])
        x2 = max(self.bbox[2], other.bbox[2])
        y2 = max(self.bbox[3], other.bbox[3])
        self.polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def intersection_area(self, other, margin=0):
        """intersection area"""
        x_overlap = max(0, min(self.bbox[2], other.bbox[2] - margin) - max(self.bbox[0], other.bbox[0] + margin))
        y_overlap = max(0, min(self.bbox[3], other.bbox[3] - margin) - max(self.bbox[1], other.bbox[1] + margin))
        return x_overlap * y_overlap

    def intersection_pct(self, other, margin=0):
        """intersection pct"""
        assert 0 <= margin <= 1
        if self.area == 0:
            return 0

        if margin:
            margin = int(min(self.width, other.width) * margin)
        intersection = self.intersection_area(other, margin)
        return intersection / self.area


class Bbox(BaseModel):
    """bbox"""
    bbox: List[float]

    @field_validator('bbox')
    @classmethod
    def check_4_elements(cls, v: List[float]) -> List[float]:
        """check 4 elements"""
        if len(v) != 4:
            raise ValueError('bbox must have 4 elements')
        return v

    def rescale_bbox(self, orig_size, new_size):
        """rescale bbox"""
        self.bbox = rescale_bbox(self.bbox, orig_size, new_size)

    def round_bbox(self, divisor):
        """round bbox"""
        self.bbox = [x // divisor * divisor for x in self.bbox]

    @property
    def height(self):
        """height"""
        return self.bbox[3] - self.bbox[1]

    @property
    def width(self):
        """width"""
        return self.bbox[2] - self.bbox[0]

    @property
    def area(self):
        """area"""
        return self.width * self.height

    @property
    def polygon(self):
        """polygon"""
        return [[self.bbox[0], self.bbox[1]], [self.bbox[2], self.bbox[1]],
            [self.bbox[2], self.bbox[3]], [self.bbox[0], self.bbox[3]]]


class LayoutBox(PolygonBox):
    """layoutbbox"""
    label: str


class OrderBox(Bbox):
    """order box"""
    position: int


class ColumnLine(Bbox):
    """columnline"""
    vertical: bool
    horizontal: bool


class TextLine(PolygonBox):
    """text line"""
    text: str
    confidence: Optional[float] = None


class OCRResult(BaseModel):
    """ocr result"""
    text_lines: List[TextLine]
    languages: List[str]
    image_bbox: List[float]


class TextDetectionResult(BaseModel):
    """text detection result"""
    bboxes: List[PolygonBox]
    vertical_lines: List[ColumnLine]
    horizontal_lines: List[ColumnLine]
    heatmap: Any
    affinity_map: Any
    image_bbox: List[float]


class LayoutResult(BaseModel):
    """layoutresult"""
    bboxes: List[LayoutBox]
    #segmentation_map: Any
    image_bbox: List[float]


class OrderResult(BaseModel):
    """order result"""
    bboxes: List[OrderBox]
    image_bbox: List[float]
