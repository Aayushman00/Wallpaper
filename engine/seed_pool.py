"""Seed pool: samples from historically high-scoring seeds, or generates fresh ones."""

from __future__ import annotations

import random

from config.settings import (
    BEST_SEED_LIMIT,
    BEST_SEED_MUTATION_RANGE,
    BEST_SEED_REUSE_PROBABILITY,
)
from database.seeds import SeedRepository

MAX_SEED = 2**63 - 1


class SeedPool:
    """Retains top-scoring seeds and samples from them with a reuse probability."""

    def __init__(self, repository: SeedRepository) -> None:
        self.repository = repository

    def next_seed(self) -> tuple[int, int | None, int]:
        """Return (seed, parent_seed, generation): a mutated top seed, or a fresh random one."""
        data = self.repository.load()

        if data and random.random() < BEST_SEED_REUSE_PROBABILITY:
            top_candidates = sorted(
                data,
                key=lambda item: item["score"],
                reverse=True,
            )[:BEST_SEED_LIMIT]

            parent = random.choice(top_candidates)
            offset = random.randint(-BEST_SEED_MUTATION_RANGE, BEST_SEED_MUTATION_RANGE)
            mutated = max(0, min(parent["seed"] + offset, MAX_SEED))
            return mutated, parent["seed"], parent.get("generation", 0) + 1

        return random.randint(0, MAX_SEED), None, 0

    def record_result(
        self,
        seeds: list[int],
        score: float,
        prompt: str,
        theme: str,
        lineage: list[tuple[int | None, int]] | None = None,
    ) -> None:
        """Store seeds ranked by their score, retaining only the top records."""
        if lineage is None:
            lineage = [(None, 0)] * len(seeds)

        data = self.repository.load()
        for index, seed in enumerate(seeds):
            parent_seed, generation = lineage[index]
            data.append({
                "seed": seed,
                "score": score,
                "sampler_index": index,
                "prompt": prompt,
                "theme": theme,
                "parent_seed": parent_seed,
                "generation": generation,
            })

        ranked = sorted(data, key=lambda item: item["score"], reverse=True)[:BEST_SEED_LIMIT]
        self.repository.save(ranked)
