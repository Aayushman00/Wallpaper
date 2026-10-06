"""Turn user likes/dislikes on past wallpapers into per-trait prompt weight multipliers."""

from __future__ import annotations

from config.settings import TASTE_MAX, TASTE_MIN, TASTE_PRIOR


def compute_taste(history: list[dict]) -> dict[str, dict[str, float]]:
    """Return {trait: {value: multiplier}} from rated history entries.

    multiplier = clamp(1 + (likes - dislikes) / (n + TASTE_PRIOR), TASTE_MIN, TASTE_MAX).
    Unrated or malformed entries are ignored; values never rated are absent (1.0).
    # ponytail: no time decay, add if taste drift matters.
    """
    likes: dict[tuple[str, str], int] = {}
    dislikes: dict[tuple[str, str], int] = {}

    if not isinstance(history, list):
        return {}

    for record in history:
        if not isinstance(record, dict):
            continue
        rating = record.get("rating")
        if type(rating) is not int or rating not in (1, -1):
            continue
        dna = record.get("dna")
        if not isinstance(dna, dict):
            continue
        counts = likes if rating == 1 else dislikes
        for trait, value in dna.items():
            if isinstance(trait, str) and isinstance(value, str):
                counts[(trait, value)] = counts.get((trait, value), 0) + 1

    taste: dict[str, dict[str, float]] = {}
    for trait, value in set(likes) | set(dislikes):
        up = likes.get((trait, value), 0)
        down = dislikes.get((trait, value), 0)
        raw = 1 + (up - down) / (up + down + TASTE_PRIOR)
        taste.setdefault(trait, {})[value] = max(TASTE_MIN, min(raw, TASTE_MAX))
    return taste


def taste_extremes(
    taste: dict[str, dict[str, float]],
    n: int = 3,
) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, float]]]:
    """Return (most boosted, most penalized) as (trait, value, multiplier) lists."""
    flat = [
        (trait, value, multiplier)
        for trait, values in taste.items()
        for value, multiplier in values.items()
    ]
    boosted = sorted((t for t in flat if t[2] > 1), key=lambda t: -t[2])[:n]
    penalized = sorted((t for t in flat if t[2] < 1), key=lambda t: t[2])[:n]
    return boosted, penalized
