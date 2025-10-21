"""
layout detection create a predictor
Author: 1329239119@qq.com
"""

from detectron2.config import instantiate
from PIL import Image
import argparse
from detectron2.checkpoint import DetectionCheckpointer
import detectron2.data.transforms as T
import torch
import cv2
from glob import glob
import numpy as np
import os
from tqdm import tqdm
from collections import defaultdict
from typing import Dict, List
from src.rock.settings import settings
import src.config_util as cfg
from src.rock.schema import LayoutResult, LayoutBox, TextDetectionResult
from detectron2.config import LazyCall as L
from detectron2.layers import ShapeSpec
from detectron2.modeling.backbone import SwinTransformer
from loguru import logger


from src.rock.model.layout.models.dab_detr import model as dab_detr_model
from src.rock.model.layout.models.dino_swin import model as dino_swin_model


id2name = {
    1: 'doc_title',
    2: 'text_title',
    3: 'text',
    4: 'table',
    5: 'figure',
    6: 'table_title',
    7: 'figure_title',
    8: 'header',
    9: 'footer',
    10: "footnote",
    11: "contents",
    12: "box",
    13: "formula"
}

name2id = {
    'doc_title': 1,
    'text_title': 2,
    'text': 3,
    'table': 4,
    'figure': 5,
    'table_title': 6,
    'figure_title': 7,
    'header': 8,
    'footer': 9,
    'footnote': 10,
    'contents': 11,
    'box': 12,
    'formula': 13
}


class DefaultPredictor:
    """
    Create a simple end-to-end predictor with the given config that runs on
    single device for a single input image.

    Compared to using the model directly, this class does the following additions:

    1. Load checkpoint from `cfg.MODEL.WEIGHTS`.
    2. Always take BGR image as the input and apply conversion defined by `cfg.INPUT.FORMAT`.
    3. Apply resizing defined by `cfg.INPUT.{MIN,MAX}_SIZE_TEST`.
    4. Take one input image and produce a single output, instead of a batch.

    This is meant for simple demo purposes, so it does the above steps automatically.
    This is not meant for benchmarks or running complicated inference logic.
    If you'd like to do anything more complicated, please refer to its source code as
    examples to build and use the model manually.

    Attributes:
        metadata (Metadata): the metadata of the underlying dataset, obtained from
            cfg.DATASETS.TEST.

    Examples:
    ::
        pred = DefaultPredictor(cfg)
        inputs = cv2.imread("input.jpg")
        outputs = pred(inputs)
    """

    def __init__(self, model, checkpoint):

        self.model = model
        self.model.eval()

        checkpointer = DetectionCheckpointer(self.model)
        checkpointer.load(checkpoint)

        self.aug = T.ResizeShortestEdge(short_edge_length=800)


    def __call__(self, original_images: List[np.ndarray], batch_size: int =16):
        """
        Args:
            original_image list of images (np.ndarray): images of shape (H, W, C) (in BGR order).

        Returns:
            predictions (dict):
                the output of the model for one image only.
                See :doc:`/tutorials/models` for details about the format.
        """
        
        results = [None] * len(original_images)
        with torch.no_grad():  # https://github.com/sphinx-doc/sphinx/issues/4258
            # Apply pre-processing to image.
            ratio_dict = group_images_with_same_ratio(original_images)
            for ratio, image_idxs in ratio_dict.items():
                same_size_images = [original_images[idx] for idx in image_idxs]
            
                for i in range(0, len(same_size_images), batch_size):
                    batch = same_size_images[i: i + batch_size]
                    batch_image_idx = image_idxs[i: i + batch_size]
                    batch_images = []

                    logger.info("layout process start")

                    for original_image in batch:
                        
                        height, width = original_image.shape[:2]

                        image = self.aug.get_transform(original_image).apply_image(original_image)

                        image = torch.as_tensor(image.astype("float32").transpose(2, 0, 1)).to(settings.TORCH_DEVICE_MODEL)

                        batch_images.append({"image": image, "height": height, "width": width})
                    
                    logger.info("layout process end")
                    predictions = self.model(batch_images)

                    for pid, prediction in zip(batch_image_idx, predictions):

                        pred_boxes = prediction["instances"].pred_boxes.to('cpu')

                        pred_classes = prediction["instances"].pred_classes.to('cpu').numpy()
                        pred_scores = prediction["instances"].scores.to('cpu').numpy()
                        
                        boxes = []
                        for index, box in enumerate(pred_boxes):
                            if pred_scores[index] > 0.35:
                                l, t, r, b = box
                                bbox = np.array([[l, t], [r, t], [r, b], [l, b]], dtype=np.int32)
                                confidence = pred_scores[index]
                                category = id2name[int(pred_classes[index]) + 1]
                                boxes.append(LayoutBox(polygon=bbox, confidence=confidence, label=category))

                        results[pid] = LayoutResult(bboxes=boxes, 
                                                        image_bbox=[0, 0,  
                                                                    prediction["instances"].image_size[1], 
                                                                    prediction["instances"].image_size[0]
                                                                    ]
                                                    )

            return results

def group_images_with_same_ratio(images):
    """
    group image with same aspect ratio
    """
    ratio_dict = defaultdict(list)
    for index, image in enumerate(images):
        height, width = image.shape[:2]
        ratio = width / height
        ratio_dict[ratio].append(index)
    return ratio_dict


def load_gpu_model(checkpoint=cfg.GPU_LAYOUT_MODEL_PATH, device=cfg.DEVICE):
    """
    load gpu model, dino only support run on gpu
    """

    model = instantiate(dino_swin_model).to(device)
    predictor = DefaultPredictor(model, checkpoint)
    return predictor


def load_cpu_model(checkpoint=cfg.CPU_LAYOUT_MODEL_PATH, device=cfg.DEVICE):
    """
    load cpu model
    """
    model = instantiate(dab_detr_model).to(device)
    predictor = DefaultPredictor(model, checkpoint)
    return predictor

    
def batch_layout_detection(images: List, predictor, batch_size=12) -> List[LayoutResult]:
    """
    batch layout detection
    """
    images = [np.asarray(image) for image in images]
    results = predictor(images, batch_size=batch_size)
    return results


