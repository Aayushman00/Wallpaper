

from __future__ import annotations

# import logging
import torch 
import clip
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-L/14", device=device)

def score(image_path, prompt):
    img = Image.open(image_path).convert("RGB")
    image = preprocess(img).unsqueeze(0).to(device)

    text = clip.tokenize([prompt]).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)

        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).item()

    score = (similarity + 1) / 2 * 100
    print(f"score={score}")
    return score
    
