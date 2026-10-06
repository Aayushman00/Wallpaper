"""Seed pool: samples from historically high-scoring seeds, or generates fresh ones."""

from __future__ import annotations

import random
import threading

from config.settings import (
    BEST_SEED_LIMIT,
    BEST_SEED_MUTATION_RANGE,
    BEST_SEED_REUSE_PROBABILITY,
    SEED_RATING_DISLIKE_MULTIPLIER,
    SEED_RATING_LIKE_MULTIPLIER,
)
from database.seeds import SeedRepository

MAX_SEED = 2**63 - 1


class SeedPool:
    """Retains top-scoring seeds and samples from them with a reuse probability."""

    def __init__(self, repository: SeedRepository) -> None:
        self.repository = repository
        self._lock = threading.Lock()

    def next_seed(self) -> tuple[int, int | None, int]:
        """Return (seed, parent_seed, generation): a mutated top seed, or a fresh random one."""
        with self._lock:
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

        with self._lock:
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

    def rate_current(self, seeds: list[int], liked: bool) -> None:
        """Scale the stored score of the given seeds up (liked) or down (disliked)."""
        multiplier = SEED_RATING_LIKE_MULTIPLIER if liked else SEED_RATING_DISLIKE_MULTIPLIER
        self._rescore(seeds, lambda score: score * multiplier)

    def penalize(self, seeds: list[int]) -> None:
        """Zero the stored score of the given seeds (quarantined generations)."""
        self._rescore(seeds, lambda score: 0.0)

    def _rescore(self, seeds: list[int], transform) -> None:
        with self._lock:
            data = self.repository.load()
            hit = False
            for record in data:
                if record["seed"] in seeds:
                    record["score"] = transform(record["score"])
                    hit = True
            if hit:
                self.repository.save(data)
