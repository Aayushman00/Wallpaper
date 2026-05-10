"""Semantic-prompt scoring logic."""
from __future__ import annotations

import logging
import torch 
import clip
from PIL import Image
from pathlib import Path

from core.clip_manager import (
    device,
    model,
    preprocess,
)

class SemanticPromptScorer:
    """CLIP-based semantic similarity score"""

    def __init__(self) -> None:
        
        self.device = device
        logging.info(
            "Loading CLIP model on %s",
            self.device
        )
        
        self.model, self.preprocess = model, preprocess

        logging.info("CLIP model loaded successfully")

    def score(
            self,
            image_path: str,
            prompt: str
    ) -> float:
        
        try: 
            if not Path(image_path).exists():
                raise FileNotFoundError(image_path)
            
            logging.info(
                "starting CLIP scoring for %s", 
                image_path
            )

            with Image.open(image_path) as img:
                image = self.preprocess(
                    img.convert("RGB")
                ).unsqueeze(0).to(self.device)

            text = clip.tokenize([prompt]).to(
                self.device
            )

            with torch.no_grad():
                image_features = (
                    self.model.encode_image(image)
                )

                text_features = (
                    self.model.encode_text(text)
                )

                image_features /= (
                    image_features.norm(
                        dim=-1,
                        keepdim=True,
                    )
                )

                text_features /= (
                    text_features.norm(
                        dim=-1,
                        keepdim=True,
                    )
                )

                similarity = (
                    image_features
                    @ text_features.T
                ).item()

                score = ((similarity + 1) / 2) * 100

                logging.info(
                    "CLIP score: %.2f",
                    score,
                )
            
            return round(score, 2)

        except Exception as e:

            logging.exception(
                "CLIP scoring failed: %s",
                e,
            )

            return 0.0

