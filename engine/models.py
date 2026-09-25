"""Domain data shapes shared between the engine and any generation backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GenerationRequest:
    prompt: str
    dna: dict[str, object]


@dataclass
class GenerationResult:
    image_path: Path
    used_seeds: list[int]
    generation_time_seconds: float


@dataclass
class EvaluationResult:
    semantic_score: float
    aesthetic_score: float
    combined_score: float
