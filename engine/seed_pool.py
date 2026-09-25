"""Seed pool: samples from historically high-scoring seeds, or generates fresh ones."""

from __future__ import annotations

import random

from config.settings import BEST_SEED_LIMIT, BEST_SEED_REUSE_PROBABILITY
from database.seeds import SeedRepository


class SeedPool:
    """Retains top-scoring seeds and samples from them with a reuse probability."""

    def __init__(self, repository: SeedRepository) -> None:
        self.repository = repository

    def next_seed(self) -> int:
        """Return a seed sampled from the top-performing pool, or a fresh random seed."""
        data = self.repository.load()

        if data and random.random() < BEST_SEED_REUSE_PROBABILITY:
            top_candidates = sorted(
                data,
                key=lambda item: item["score"],
                reverse=True,
            )[:BEST_SEED_LIMIT]

            return random.choice(top_candidates)["seed"]

        return random.randint(0, 2**63 - 1)

    def record_result(
        self,
        seeds: list[int],
        score: float,
        prompt: str,
        theme: str,
    ) -> None:
        """Store seeds ranked by their score, retaining only the top records."""
        data = self.repository.load()
        for index, seed in enumerate(seeds):
            data.append({
                "seed": seed,
                "score": score,
                "sampler_index": index,
                "prompt": prompt,
                "theme": theme,
            })

        ranked = sorted(data, key=lambda item: item["score"], reverse=True)[:BEST_SEED_LIMIT]
        self.repository.save(ranked)
