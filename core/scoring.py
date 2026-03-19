"""Prompt scoring logic."""

from __future__ import annotations

import random


GOOD_WORDS = [
    "volumetric lighting",
    "ray traced lighting",
    "global illumination",
    "ultra wide",
    "cinematic",
    "epic",
]

BAD_WORDS = [
    "low quality",
    "blurry",
]


class PromptScorer:
    """Applies the original prompt scoring heuristic."""

    def score(self, prompt: str) -> float:
        """Calculate a bounded score from 0 to 100."""
        score = 50

        for word in GOOD_WORDS:
            if word in prompt:
                score += 8

        for word in BAD_WORDS:
            if word in prompt:
                score -= 15

        score += random.uniform(-5, 5)
        return max(0, min(100, score))
