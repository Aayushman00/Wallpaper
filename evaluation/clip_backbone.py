from __future__ import annotations

import clip
import torch


device = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

model, preprocess = clip.load(
    "ViT-L/14",
    device=device,
)

model.eval()