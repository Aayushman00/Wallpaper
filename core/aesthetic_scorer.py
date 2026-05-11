"""Prompt scoring logic."""
from __future__ import annotations

import logging
import torch 
from PIL import Image
from torch import nn
from pathlib import Path

from core.clip_manager import (
    device,
    model,
    preprocess,
)

class AestheticScorer:

    def __init__(self):
        self.device = device

        logging.info(
            "Loading aesthetic scorer on %s",
            self.device
        )

        self.model, self.preprocess = model, preprocess

        self.predictor = nn.Linear(
            768,
            1,
        )

        weights_path = (
            Path(__file__).resolve().parent
            / "sa_0_4_vit_l_14_linear.pth"
        )

        self.predictor.load_state_dict(
            torch.load(
                weights_path,
                map_location=self.device,
            )
        )

        self.predictor.to(self.device)
        self.predictor.eval()

        logging.info(
            "Aesthetic scorer loaded"
        )

    def score(
            self, 
            image_path: str,
    ) -> float:
        
        with Image.open(image_path) as img:
            image = self.preprocess(
                img = self.preprocess(
                    img.convert("RGB")
                )
            ).unsqueeze(0).to(self.device)

        with torch.no_grad():

            features = (
                self.model.encode_image(image)
            )

            features /= (
                features.norm(
                    dim=-1,
                    keepdim=True,
                )
            )

            score = (
                self.predictor(
                    features.float()
                )
                .cpu()
                .item()
            )

        logging.info(
            "Aesthetic score: %.2f",
            score,
        )

        return round(score, 2)

