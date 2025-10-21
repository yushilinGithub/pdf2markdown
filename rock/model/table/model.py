# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2024 , Inc. All Rights Reserved
#
################################################################################
"""
表格识别模块。

Authors: yushilin(1329239119@qq.com)
Date:    2024/07/29 17:08:41
"""

from src.rock.model.table.components import EncoderDecoder, ImgLinearBackbone, Encoder, Decoder
from src.rock.model.table.utils import (
    subsequent_mask,
    pred_token_within_range, 
    greedy_sampling, 
    bbox_str_to_token_list, 
    cell_str_to_token_list, 
    html_str_to_token_list, 
    build_table_from_html_and_cell,
    html_table_template
    )
from src.rock.model.table.vocab import VALID_HTML_TOKEN, VALID_BBOX_TOKEN, INVALID_CELL_TOKEN 
from torch import nn, Tensor
from loguru import logger
from functools import partial
from bs4 import BeautifulSoup as bs
from typing import Tuple, List, Sequence, Optional, Union
from PIL import Image
from src.rock.settings import settings
import re
import torch
import tokenizers as tk
from torchvision import transforms
import os


def autoregressive_decode(
    model: EncoderDecoder,
    image: Tensor,
    prefix: Sequence[int],
    max_decode_len: int,
    eos_id: int,
    token_whitelist: Optional[Sequence[int]] = None,
    token_blacklist: Optional[Sequence[int]] = None,
    device: str = "cuda"
) -> Tensor:
    """autoregressive_decode"""
    model.eval()
    with torch.no_grad():
        memory = model.encode(image)
        context = torch.tensor(prefix, dtype=torch.int32).repeat(image.shape[0], 1).to(device)

    for _ in range(max_decode_len):
        eos_flag = [eos_id in k for k in context]
        if all(eos_flag):
            break

        with torch.no_grad():
            causal_mask = subsequent_mask(context.shape[1]).to(device)
            logits = model.decode(
                memory, context, tgt_mask=causal_mask, tgt_padding_mask=None
            )
            logits = model.generator(logits)[:, -1, :]

        logits = pred_token_within_range(
            logits.detach(),
            white_list=token_whitelist,
            black_list=token_blacklist,
        )
        next_probs, next_tokens = greedy_sampling(logits)
        context = torch.cat([context, next_tokens], dim=1)
    return context


def image_to_tensor(image: Image, size: Tuple[int, int]) -> Tensor:
    """image_to_tensor"""
    T = transforms.Compose([
        transforms.Resize(size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.86597056, 0.88463002, 0.87491087], std=[0.20686628, 0.18201602, 0.18485524])
    ])

    image_tensor = T(image)
    image_tensor = image_tensor.unsqueeze(0)

    return image_tensor


def rescale_bbox(
    bbox: Sequence[Sequence[float]],
    src: Tuple[int, int],
    tgt: Tuple[int, int]
) -> Sequence[Sequence[float]]:
    """rescale_bbox"""
    assert len(src) == len(tgt) == 2
    ratio = [tgt[0] / src[0], tgt[1] / src[1]] * 2
    bbox = [[int(round(i * j)) for i, j in zip(entry, ratio)] for entry in bbox]
    return bbox



class Predictor():
    """predictor"""
    def __init__(self, 
                structure_vocab_path=settings.TABLE_STRUCTURE_VOCAB, 
                bbox_vocab_path=settings.TABLE_BBOX_VOCAB, 
                structure_model_path=settings.TABLE_STRUCTURE_MODEL, 
                bbox_model_path=settings.TABLE_BBOX_MODEL,
                device="cuda",):
        
        self.device = device
        
        # UniTable large model
        d_model = 768
        patch_size = 16
        nhead = 12
        dropout = 0.2

        # Initialize the structure model components
        structure_backbone = ImgLinearBackbone(d_model=d_model, patch_size=patch_size)
        structure_encoder = Encoder(
            d_model=d_model,
            nhead=nhead,
            dropout=dropout,
            activation="gelu",
            norm_first=True,
            nlayer=12,
            ff_ratio=4,
        )
        structure_decoder = Decoder(
            d_model=d_model,
            nhead=nhead,
            dropout=dropout,
            activation="gelu",
            norm_first=True,
            nlayer=4,
            ff_ratio=4,
        )
        self.structure_vocab = tk.Tokenizer.from_file(structure_vocab_path)
        self.structure_model = EncoderDecoder(
            backbone=structure_backbone,
            encoder=structure_encoder,
            decoder=structure_decoder,
            vocab_size=self.structure_vocab.get_vocab_size(),
            d_model=d_model,
            padding_idx=self.structure_vocab.token_to_id("<pad>"),
            max_seq_len=784,
            dropout=dropout,
            norm_layer=partial(nn.LayerNorm, eps=1e-6)
        )
        structure_model_dict = torch.load(structure_model_path, map_location="cpu")
        self.structure_model.load_state_dict(structure_model_dict)
        self.structure_model = self.structure_model.to(device)
        self.structure_model.eval()

        # Initialize the bbox model components
        bbox_backbone = ImgLinearBackbone(d_model=d_model, patch_size=patch_size)
        bbox_encoder = Encoder(
            d_model=d_model,
            nhead=nhead,
            dropout=dropout,
            activation="gelu",
            norm_first=True,
            nlayer=12,
            ff_ratio=4,
        )
        bbox_decoder = Decoder(
            d_model=d_model,
            nhead=nhead,
            dropout=dropout,
            activation="gelu",
            norm_first=True,
            nlayer=4,
            ff_ratio=4,
        )
        self.bbox_vocab = tk.Tokenizer.from_file(bbox_vocab_path)
        self.bbox_model = EncoderDecoder(
            backbone=bbox_backbone,
            encoder=bbox_encoder,
            decoder=bbox_decoder,
            vocab_size=self.bbox_vocab.get_vocab_size(),
            d_model=d_model,
            padding_idx=self.bbox_vocab.token_to_id("<pad>"),
            max_seq_len=1024,
            dropout=dropout,
            norm_layer=partial(nn.LayerNorm, eps=1e-6)
        )
        bbox_model_dict = torch.load(bbox_model_path, map_location="cpu")
        self.bbox_model.load_state_dict(bbox_model_dict)
        self.bbox_model = self.bbox_model.to(device)
        self.bbox_model.eval()
        

    def __call__(self, images, batch_size=24):
        """__call__"""

        result_bbox, result_structure = [], []

        for i in range(0, len(images), batch_size):
            batch = images[i: i + batch_size]
            image_sizes = [(img.width, img.height) for img in batch]
            image_tensor = torch.cat([image_to_tensor(img, size=(448, 448)) for img in batch], dim=0).to(self.device)

        

            logger.info("start table html predict")
            pred_html = autoregressive_decode(
                                    model=self.structure_model,
                                    image=image_tensor,
                                    prefix=[self.structure_vocab.token_to_id("[html]")],
                                    max_decode_len=512,
                                    eos_id=self.structure_vocab.token_to_id("<eos>"),
                                    token_whitelist=[self.structure_vocab.token_to_id(i) for i in VALID_HTML_TOKEN],
                                    token_blacklist=None
                                            )
            
            # Convert token id to token text
            pred_htmls = pred_html.detach().cpu().numpy()
            logger.info("finish table html predict")
            for pred_html in pred_htmls:
                pred_html = self.structure_vocab.decode(pred_html, skip_special_tokens=False)
                result_structure.append(html_str_to_token_list(pred_html))


            # Inference bbox
            logger.info("start table box recognition")
            pred_bbox = autoregressive_decode(
                            model=self.bbox_model,
                            image=image_tensor,
                            prefix=[self.bbox_vocab.token_to_id("[bbox]")],
                            max_decode_len=1024,
                            eos_id=self.bbox_vocab.token_to_id("<eos>"),
                            token_whitelist=[self.bbox_vocab.token_to_id(i) for i in VALID_BBOX_TOKEN[: 449]],
                            token_blacklist=None
                        )

            # Convert token id to token text
            pred_bboxes = pred_bbox.detach().cpu().numpy()
            for pred_bbox, image_size in zip(pred_bboxes, image_sizes):
                pred_bbox = self.bbox_vocab.decode(pred_bbox, skip_special_tokens=False)
                pred_bbox = bbox_str_to_token_list(pred_bbox)
                result_bbox.append(rescale_bbox(pred_bbox, src=(448, 448), tgt=image_size))
            logger.info("finish table bbox recognition")
        return result_bbox, result_structure

    
def load_table_model(checkpoint, device="cuda"):
    """
    load table model from checkpoint
    """
    structure_vocab_path = os.path.join(checkpoint, "vocab_html.json")
    bbox_vocab_path = os.path.join(checkpoint, "vocab_bbox.json")
    structure_model_path = os.path.join(checkpoint, "unitable_large_structure.pt")
    bbox_model_path = os.path.join(checkpoint, "unitable_large_bbox.pt")
    # Load the checkpoint file and create a new instance of the model
    model = Predictor(structure_vocab_path, bbox_vocab_path, structure_model_path, bbox_model_path, device=device)
    return model
