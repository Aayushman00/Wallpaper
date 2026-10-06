"""Domain data shapes shared between the engine and any generation backend."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    used_lineage: list[tuple[int | None, int]] = field(default_factory=list)


@dataclass
class CycleResult:
    image_path: Path
    used_seeds: list[int]
    generation: int
    quarantined: bool = False


@dataclass
class EvaluationResult:
    semantic_score: float
    aesthetic_score: float
    combined_score: float
