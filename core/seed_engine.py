"""Seed evolution logic."""

from __future__ import annotations

import random

from config.constants import (
    BEST_SEED_LIMIT,
    BEST_SEED_MUTATION_RANGE,
    BEST_SEED_REUSE_PROBABILITY,
)
from database.seeds import SeedRepository


class SeedEngine:
    """Generates new seeds and maintains best-seed history."""

    def __init__(self, repository: SeedRepository) -> None:
        self.repository = repository

    def get_seed(self) -> int:
        """Return an evolved seed or a new random seed."""
        data = self.repository.load()

        if data and random.random() < BEST_SEED_REUSE_PROBABILITY:
            
            top_candidates = sorted(
                data,
                key=lambda item: item["score"],
                reverse=True,
            )[:BEST_SEED_LIMIT]

            parent = random.choice(top_candidates)["seed"]
            
            # new_seed = parent + random.randint(-BEST_SEED_MUTATION_RANGE, BEST_SEED_MUTATION_RANGE) 
            # seed mutation disabled for now
            
            return parent
        
        return random.randint(0, 2**63 - 1)

    def update(self, 
               seeds: list[int], 
               score: float,
               prompt: str,
               theme: str,
               ) -> None:
        """Store seeds ranked by their score, retaining only the top records."""
        data = self.repository.load()
        for ind, seed in enumerate(seeds):
            data.append({
                        "seed": seed, 
                        "score": score,
                        "sampler_index": ind,
                        "prompt": prompt,
                        "theme":theme,
            })

        ranked = sorted(data, key=lambda item: item["score"], reverse=True)[:BEST_SEED_LIMIT]
        self.repository.save(ranked)
