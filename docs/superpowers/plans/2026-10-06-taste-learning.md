# Taste Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record each like/dislike against the rated image's prompt traits (`dna`) and bias future prompt generation toward traits you rate well and away from traits you rate poorly — gently, with an exploration floor.

**Architecture:** `HistoryRepository.set_rating` stores `rating: ±1` on the newest history entry for an image (idempotent). A pure `compute_taste(history)` turns rated entries into per-(trait, value) weight multipliers, shrunk toward 1.0 with a prior and clamped to `[TASTE_MIN, TASTE_MAX]`. The daemon recomputes taste each cycle and passes it through `WallpaperEngine.run(taste=...)` to `PromptEngine.generate(taste=...)`, which multiplies pick weights through one helper. Taste is applied after compatibility filtering and the existing context/diversity weighting, immediately before the final selection call (the density guard inside `pick_weighted_with_density` still applies on top of it). Recording a rating in history is best-effort: it can never break the existing seed rescoring.

**Tech Stack:** Python 3.13, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-06-taste-learning-design.md`

**Prerequisite:** branch `feature/evolution-daemon` (the daemon, `current_state.json`, `PromptEngine.generate(context=...)`). Work on a branch cut from it, e.g. `feature/taste-learning`.

## Global Constraints

- No new dependencies; local Windows side project; no ABC/Protocol for single implementations.
- `PromptEngine.generate()` with no arguments, and with `context` only, behaves exactly as before; `tests/generation/test_prompt_engine.py` existing tests pass unmodified.
- `WallpaperEngine.run()` keeps working with fakes whose `generate()` takes no arguments: `context`/`taste` are passed only when truthy.
- Existing like/dislike seed-rescoring (`SeedPool.rate_current`) is unchanged and still runs.
- `history.json` entries without `rating` are valid (unrated); no migration.
- A taste failure must never block or kill a generation cycle.
- Recording a rating in history is best-effort: if `set_rating` raises or returns `False`, log it and still call `seed_pool.rate_current`.
- `HistoryRepository.set_rating` accepts only `+1` and `-1` (exact ints; `True`, `0`, `1.0`, strings, `None` raise `ValueError`).
- Taste is applied after compatibility filtering and existing context/diversity weighting, immediately before the final selection call.
- Constants (exact): `TASTE_PRIOR = 3`, `TASTE_MIN = 0.4`, `TASTE_MAX = 2.0`.
- Test runner: `"C:\Python313\python.exe" -m pytest <path> -v`.
- Test file basenames must be unique across `tests/` (no `__init__.py`): new tests use `test_taste_model.py`.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Source files may use CRLF line endings; prefer whole-file rewrites or edits that tolerate that (Edit tool works on exact text; if a multi-line match fails, retry with CRLF).

## Review Focus

1. **Silent no-op steering** — a hooked trait name that doesn't match a `dna` key disables that trait's steering with no error. Expected: every hooked trait is consulted and is a `dna` key. Pinned in Task 4.
2. **Rating lost, doubled, or invalid** — rating the same image twice must store one value; rating an image missing from history must not crash or corrupt; a rating other than exactly `+1`/`-1` must be rejected without writing; a failing history write must not stop the seed rescoring. Pinned in Tasks 2 and 6.
3. **Sparse data over-steering** — one or two ratings must not collapse variety. Expected: 1 like ≈ 1.25×, 1 dislike = 0.75×, floor `TASTE_MIN`. Pinned in Task 3.
4. **Taste failure blocks generation** — a corrupt/unreadable history must still produce a wallpaper. Pinned in Task 6.
5. **Concurrent history writes** — hotkey-thread rating vs scheduler append must lose nothing (Windows `replace` during a read raises `PermissionError`). Pinned in Task 2.
6. **Malformed history entries** — non-dict records, non-dict `dna`, non-string trait names/values, and invalid ratings (`0`, `2`, `True`, `1.0`, `"1"`, `None`) must be ignored, not raise. Pinned in Task 3.
7. **Taste steering through a non-theme, density-guarded pick** — pinned in Task 4 (`pick_weighted_with_density` path).

---

### Task 1: Taste constants and gene-analytics fixture fix

**Files:**
- Modify: `config/settings.py`
- Modify: `tests/test_gene_analytics.py` (fixture key)
- Test: `tests/config/test_settings.py`

**Interfaces:**
- Produces: `settings.TASTE_PRIOR`, `settings.TASTE_MIN`, `settings.TASTE_MAX`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/config/test_settings.py`:

```python
def test_taste_constants_present_and_correct():
    assert settings.TASTE_PRIOR == 3
    assert settings.TASTE_MIN == 0.4
    assert settings.TASTE_MAX == 2.0
```

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py tests/test_gene_analytics.py -v`
Expected: FAIL — `AttributeError: module 'config.settings' has no attribute 'TASTE_PRIOR'`, and the pre-existing `test_trait_averages` fails with `assert 0.0 == 70.0`.

- [ ] **Step 3: Write minimal implementation**

Append to `config/settings.py`:

```python
TASTE_PRIOR = 3
TASTE_MIN = 0.4
TASTE_MAX = 2.0
```

In `tests/test_gene_analytics.py`, change the two fixture keys `"score": 80` → `"combined_score": 80` and `"score": 60` → `"combined_score": 60` (the code under test reads `combined_score`; the fixture was wrong).

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py tests/test_gene_analytics.py -v`
Expected: PASS (all, including `test_trait_averages`).

- [ ] **Step 5: Commit**

```bash
git add config/settings.py tests/config/test_settings.py tests/test_gene_analytics.py
git commit -m "feat: add taste constants, fix gene-analytics test fixture key"
```

---

### Task 2: `HistoryRepository.set_rating` and thread-safe access

**Files:**
- Modify: `database/history.py` (full rewrite below; behavior of `load`/`append` preserved)
- Test: `tests/test_history.py`

**Interfaces:**
- Produces: `HistoryRepository.set_rating(image_path: str, rating: int) -> bool` — raises `ValueError` (before any I/O) unless `rating` is exactly the int `1` or `-1`; otherwise sets `entry["rating"]` on the **newest** entry whose `image_path` matches; `False` and no write if none. `load()`, `append(...)`, `set_rating(...)` all guarded by one `threading.RLock`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_history.py` (it already defines `_append(repo, **extra)` and imports `HistoryRepository`):

```python
import threading

import pytest


def _append_image(repo, image_path):
    repo.append(
        seeds=[1], semantic_score=50.0, aesthetic_score=5.0, combined_score=0.5,
        image_path=image_path, generation_time=1.0, semantic_prompt="p", dna={},
    )


def test_set_rating_marks_the_newest_entry_for_that_image(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    _append_image(repo, "b.png")
    _append_image(repo, "a.png")

    assert repo.set_rating("a.png", 1) is True

    first, second, third = repo.load()
    assert "rating" not in first
    assert "rating" not in second
    assert third["rating"] == 1


def test_set_rating_replaces_an_earlier_rating_instead_of_compounding(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")

    repo.set_rating("a.png", 1)
    repo.set_rating("a.png", 1)
    assert repo.load()[0]["rating"] == 1

    repo.set_rating("a.png", -1)
    assert repo.load()[0]["rating"] == -1


def test_set_rating_for_unknown_image_returns_false_and_writes_nothing(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    before = repo.path.read_text(encoding="utf-8")

    assert repo.set_rating("missing.png", 1) is False

    assert repo.path.read_text(encoding="utf-8") == before


def test_set_rating_on_empty_history_returns_false(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")

    assert repo.set_rating("a.png", 1) is False


@pytest.mark.parametrize("bad", [0, 2, -2, True, False, 1.0, "1", None])
def test_set_rating_rejects_anything_but_plus_or_minus_one_and_writes_nothing(tmp_path, bad):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    before = repo.path.read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        repo.set_rating("a.png", bad)

    assert repo.path.read_text(encoding="utf-8") == before


def test_concurrent_append_and_set_rating_lose_nothing(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "rated.png")

    def add(i):
        _append_image(repo, f"img{i}.png")

    def rate():
        for _ in range(20):
            repo.set_rating("rated.png", 1)

    threads = [threading.Thread(target=add, args=(i,)) for i in range(20)]
    threads.append(threading.Thread(target=rate))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    records = repo.load()
    assert len(records) == 21
    assert next(r for r in records if r["image_path"] == "rated.png")["rating"] == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/test_history.py -v`
Expected: FAIL — `AttributeError: 'HistoryRepository' object has no attribute 'set_rating'` (all new tests).

- [ ] **Step 3: Write minimal implementation**

Replace the whole of `database/history.py` with:

```python
"""Persistence for wallpaper generation history."""

from __future__ import annotations

import json
import os
import threading
import time
import logging
from pathlib import Path


class HistoryRepository:
    """Stores wallpaper generation metadata.

    Shared between the scheduler thread (append) and the hotkey thread
    (set_rating, revert's load), so every public method takes one lock.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def load(self) -> list[dict[str, object]]:
        """Return stored history entries, or an empty list if unavailable."""
        with self._lock:
            return self._read()

    def _read(self) -> list[dict[str, object]]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise RuntimeError(
                    f"History file must contain a list: {self.path}"
                )
            return data

        except FileNotFoundError:
            return []

        except json.JSONDecodeError as exc:
            logging.error("Failed to load %s: %s", self.path, exc)
            corrupt_path = self.path.with_suffix(".corrupt")

            self.path.replace(corrupt_path)

            raise RuntimeError(
                f"Corrupt JSON file: {self.path}"
            ) from exc

        except Exception as exc:
            raise RuntimeError(
                f"Unexpected history load failure: {self.path}"
            ) from exc

    def _write(self, records: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")

        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2)
            file.flush()
            os.fsync(file.fileno())

        tmp_path.replace(self.path)

    def append(
            self,
            seeds: list[int],
            semantic_score: float,
            aesthetic_score: float,
            combined_score: float,
            image_path: str,
            generation_time: float,
            semantic_prompt: str,
            dna: dict[str, object],
            quarantined: bool = False,
        ) -> None:
        """Append a generation record to the history file."""
        with self._lock:
            records = self._read()
            records.append(
                {
                    "seeds": seeds,
                    "semantic_score": semantic_score,
                    "aesthetic_score": aesthetic_score,
                    "combined_score": combined_score,
                    "image_path": image_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "generation_time": generation_time,
                    "semantic_prompt": semantic_prompt,
                    "dna": dna,
                }
            )

            if quarantined:
                records[-1]["quarantined"] = True

            self._write(records)

    def set_rating(self, image_path: str, rating: int) -> bool:
        """Set `rating` (+1 liked / -1 disliked) on the newest entry for `image_path`.

        Idempotent: a later rating replaces an earlier one. Returns False, writing
        nothing, if no entry has that image_path. Raises ValueError, before any I/O,
        unless rating is exactly the int 1 or -1 (bool, float, str, None are rejected).
        """
        if type(rating) is not int or rating not in (1, -1):
            raise ValueError(f"rating must be +1 or -1, got {rating!r}")

        with self._lock:
            records = self._read()
            for record in reversed(records):
                if record.get("image_path") == image_path:
                    record["rating"] = rating
                    self._write(records)
                    return True
            return False
```

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/test_history.py tests/engine -v`
Expected: PASS (all history tests incl. the pre-existing three, and engine tests).

- [ ] **Step 5: Commit**

```bash
git add database/history.py tests/test_history.py
git commit -m "feat: add HistoryRepository.set_rating and guard history access with a lock"
```

---

### Task 3: `compute_taste` and `taste_extremes`

**Files:**
- Create: `analytics/taste_model.py`
- Test: `tests/analytics/test_taste_model.py` (create `tests/analytics/`)

**Interfaces:**
- Consumes: `settings.TASTE_PRIOR/TASTE_MIN/TASTE_MAX` (Task 1); history entries shaped as in Task 2 (`dna: dict`, optional `rating: 1 | -1`).
- Produces:
  - `compute_taste(history: list[dict]) -> dict[str, dict[str, float]]` — `{trait: {value: multiplier}}`; unrated/malformed entries ignored; empty dict if nothing rated.
  - `taste_extremes(taste, n=3) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, float]]]` — `(boosted, penalized)` as `(trait, value, multiplier)`; boosted = multiplier > 1 sorted descending, penalized = multiplier < 1 sorted ascending, each at most `n`.

- [ ] **Step 1: Write the failing tests**

`tests/analytics/test_taste_model.py`:

```python
import pytest

from analytics.taste_model import compute_taste, taste_extremes
from config.settings import TASTE_MAX, TASTE_MIN


def _entry(rating=None, **dna):
    entry = {"dna": dna}
    if rating is not None:
        entry["rating"] = rating
    return entry


def test_empty_history_gives_empty_taste():
    assert compute_taste([]) == {}


def test_unrated_entries_are_ignored():
    assert compute_taste([_entry(mood="eerie"), _entry(mood="eerie")]) == {}


def test_one_like_is_a_gentle_boost():
    taste = compute_taste([_entry(1, mood="eerie")])

    assert taste["mood"]["eerie"] == pytest.approx(1.25)


def test_four_likes_boost_more_but_stay_below_the_cap():
    taste = compute_taste([_entry(1, mood="eerie")] * 4)

    assert taste["mood"]["eerie"] == pytest.approx(1 + 4 / 7)
    assert taste["mood"]["eerie"] < TASTE_MAX


def test_one_dislike_is_a_gentle_penalty():
    taste = compute_taste([_entry(-1, mood="serene")])

    assert taste["mood"]["serene"] == pytest.approx(0.75)


def test_many_dislikes_floor_at_taste_min_never_zero():
    taste = compute_taste([_entry(-1, mood="serene")] * 50)

    assert taste["mood"]["serene"] == TASTE_MIN
    assert TASTE_MIN > 0


def test_many_likes_never_exceed_taste_max():
    taste = compute_taste([_entry(1, mood="eerie")] * 1000)

    assert taste["mood"]["eerie"] <= TASTE_MAX


def test_equal_likes_and_dislikes_net_to_neutral():
    taste = compute_taste([_entry(1, mood="eerie"), _entry(-1, mood="eerie")])

    assert taste["mood"]["eerie"] == pytest.approx(1.0)


def test_each_trait_value_is_scored_independently():
    taste = compute_taste([
        _entry(1, mood="eerie", light_time="golden hour"),
        _entry(-1, mood="serene", light_time="golden hour"),
    ])

    assert taste["mood"]["eerie"] == pytest.approx(1.25)
    assert taste["mood"]["serene"] == pytest.approx(0.75)
    assert taste["light_time"]["golden hour"] == pytest.approx(1.0)


VALID = {"dna": {"mood": "eerie"}, "rating": 1}  # contributes exactly {"mood": {"eerie": 1.25}}


def _only_valid_counts(*bad_records):
    taste = compute_taste([*bad_records, VALID])
    assert taste == {"mood": {"eerie": pytest.approx(1.25)}}


def test_non_dict_records_are_ignored():
    _only_valid_counts(None, 5, "text", [1, 2], ("dna", "rating"))


def test_non_dict_dna_is_ignored():
    _only_valid_counts(
        {"dna": None, "rating": 1},
        {"dna": "eerie", "rating": 1},
        {"dna": ["mood", "eerie"], "rating": 1},
        {"dna": 7, "rating": 1},
        {"rating": 1},
    )


def test_non_string_trait_names_and_values_are_ignored():
    _only_valid_counts(
        {"dna": {1: "eerie", None: "eerie", ("a",): "eerie"}, "rating": 1},
        {"dna": {"mood": None, "lens": 3, "framing": ["wide"], "camera_angle": {"x": 1}}, "rating": 1},
        {"dna": {"scene_density_score": 7}, "rating": 1},
    )


@pytest.mark.parametrize("bad", [0, 2, -2, True, False, 1.0, -1.0, "1", "like", None, [1], {"v": 1}])
def test_invalid_ratings_are_ignored(bad):
    _only_valid_counts({"dna": {"mood": "eerie"}, "rating": bad})


def test_non_list_history_gives_empty_taste():
    assert compute_taste(None) == {}
    assert compute_taste("history") == {}
    assert compute_taste({"rating": 1}) == {}


def test_taste_extremes_orders_and_limits():
    taste = {
        "mood": {"a": 1.5, "b": 1.25, "c": 1.1, "d": 1.05, "e": 0.75, "f": 0.5},
        "lens": {"g": 1.0},
    }

    boosted, penalized = taste_extremes(taste, n=3)

    assert boosted == [("mood", "a", 1.5), ("mood", "b", 1.25), ("mood", "c", 1.1)]
    assert penalized == [("mood", "f", 0.5), ("mood", "e", 0.75)]


def test_taste_extremes_of_empty_taste():
    assert taste_extremes({}) == ([], [])
```

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/analytics/test_taste_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'analytics.taste_model'`.

- [ ] **Step 3: Write minimal implementation**

`analytics/taste_model.py`:

```python
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
```

(`type(rating) is not int` is checked explicitly because `True == 1` and `1.0 == 1` in Python; `rating not in (1, -1)` alone would let a boolean or float through. The function never raises on malformed input.)

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/analytics/test_taste_model.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add analytics/taste_model.py tests/analytics/test_taste_model.py
git commit -m "feat: add compute_taste and taste_extremes"
```

---

### Task 4: Apply taste in `PromptEngine`

**Files:**
- Modify: `generation/prompt_engine.py`
- Test: `tests/generation/test_prompt_engine.py`

**Interfaces:**
- Consumes: taste dict shape from Task 3 (`{trait: {value: multiplier}}`).
- Produces:
  - `PromptEngine.generate(context: dict | None = None, taste: dict | None = None)`.
  - `PromptEngine.TASTE_TRAITS: tuple[str, ...]` — the hooked `dna` keys.
  - `PromptEngine._taste_multiplier(taste, trait, label) -> float` (staticmethod); `PromptEngine._apply_taste(items, trait, taste) -> list[dict]` (returns `items` unchanged when `taste` is falsy; never mutates input; scales `weight` by label). Applied after compatibility filtering and existing context/diversity weighting, immediately before the final selection call.

- [ ] **Step 1: Write the failing tests**

Append to `tests/generation/test_prompt_engine.py` (it already imports `PromptEngine` and `THEMES`):

```python
import random

from config.settings import TASTE_MAX, TASTE_MIN

TASTE_POOL = [
    {"label": "a", "weight": 1.0},
    {"label": "b", "weight": 2.0},
    {"label": "c", "weight": 0.5},
]


def test_apply_taste_is_a_noop_without_taste():
    engine = PromptEngine()

    assert engine._apply_taste(TASTE_POOL, "mood", None) == TASTE_POOL
    assert engine._apply_taste(TASTE_POOL, "mood", {}) == TASTE_POOL


def test_apply_taste_scales_matching_labels_and_does_not_mutate_input():
    taste = {"mood": {"a": 1.5, "b": 0.4}}

    result = PromptEngine()._apply_taste(TASTE_POOL, "mood", taste)

    assert [i["weight"] for i in result] == pytest.approx([1.5, 0.8, 0.5])
    assert [i["weight"] for i in TASTE_POOL] == [1.0, 2.0, 0.5]


def test_apply_taste_ignores_other_traits_and_unknown_labels():
    result = PromptEngine()._apply_taste(TASTE_POOL, "mood", {"lens": {"a": 2.0}, "mood": {"zzz": 2.0}})

    assert result == TASTE_POOL


def test_generate_with_taste_returns_expected_shape():
    result = PromptEngine().generate(taste={"mood": {"nothing": 1.0}})

    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES


def test_generate_consults_taste_for_every_hooked_trait(monkeypatch):
    seen = set()
    original = PromptEngine._taste_multiplier

    def spy(taste, trait, label):
        seen.add(trait)
        return original(taste, trait, label)

    monkeypatch.setattr(PromptEngine, "_taste_multiplier", staticmethod(spy))

    result = PromptEngine().generate(taste={"mood": {"nothing": 1.0}})

    assert seen == set(PromptEngine.TASTE_TRAITS)
    assert set(PromptEngine.TASTE_TRAITS) <= set(result["dna"])


def test_taste_steers_theme_choice_toward_the_boosted_value():
    random.seed(1234)
    themes = list(THEMES)
    taste = {"theme": {name: (TASTE_MAX if name == themes[0] else TASTE_MIN) for name in themes}}
    engine = PromptEngine()

    picks = [engine.generate(taste=taste)["dna"]["theme"] for _ in range(300)]

    assert picks.count(themes[0]) / 300 > 1 / len(themes) + 0.15


@pytest.mark.parametrize("current_density", [0, MAX_SCENE_DENSITY])
def test_taste_steers_non_theme_picks_through_pick_weighted_with_density(current_density):
    random.seed(99)
    engine = PromptEngine()
    pool = [{"label": "liked", "weight": 1.0}, {"label": "disliked", "weight": 1.0}]
    taste = {"environment": {"liked": TASTE_MAX, "disliked": TASTE_MIN}}
    weighted = engine._apply_taste(pool, "environment", taste)

    picks = [
        engine.pick_weighted_with_density(weighted, current_density)["label"]
        for _ in range(500)
    ]

    # expected share 2.0 / (2.0 + 0.4) = 0.83, in both the normal and the density-guarded path
    assert picks.count("liked") / 500 > 0.7
```
Add `import pytest` at the top of the file if absent, and extend the existing `from config.settings import ...` area with `from config.prompt_grammar import MAX_SCENE_DENSITY`.

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/test_prompt_engine.py -v`
Expected: FAIL — `AttributeError: 'PromptEngine' object has no attribute '_apply_taste'`; `generate() got an unexpected keyword argument 'taste'`.

- [ ] **Step 3: Write minimal implementation**

In `generation/prompt_engine.py`:

(a) Add inside `PromptEngine`, directly above the `# Context-aware lighting bias` comment block:

```python
    # -------------------------------------------------------------------------
    # Taste bias — multiplies pick weights by learned per-trait multipliers
    # -------------------------------------------------------------------------

    TASTE_TRAITS = (
        "theme", "subject", "location", "environment", "light_time", "light_quality",
        "mood", "framing", "lens", "camera_angle", "render_medium", "quality_marker",
        "environmental_condition",
    )

    @staticmethod
    def _taste_multiplier(taste: dict | None, trait: str, label: str) -> float:
        return (taste or {}).get(trait, {}).get(label, 1.0)

    def _apply_taste(
        self,
        items: list[dict],
        trait: str,
        taste: dict | None,
    ) -> list[dict]:
        if not taste:
            return items
        return [
            {**item, "weight": item["weight"] * self._taste_multiplier(taste, trait, item["label"])}
            for item in items
        ]
```

(b) Change the signature to `def generate(self, context: dict | None = None, taste: dict | None = None) -> dict[str, object]:`.

(c) Apply these exact edits inside `generate`. Ordering rule: taste is applied **after** compatibility filtering and the existing context/diversity weighting, **immediately before** the final selection call (`pick_weighted` / `pick_weighted_with_density`); the density guard inside `pick_weighted_with_density` still applies on top, and taste can never revive a filtered-out item because it only rescales items already in the pool. Each "find" line appears once in the file; insert the new line immediately **before** it unless noted:

| Find (existing line) | Change |
|---|---|
| `theme_name = random.choice(list(THEMES.keys()))` | Replace with the block below (theme) |
| `subject = random.choices(` ... (the 5-line block with `weights=theme_data["subject_weights"],`) | Replace `weights=theme_data["subject_weights"],` with `weights=[w * self._taste_multiplier(taste, "subject", s["label"]) for s, w in zip(theme_data["subjects"], theme_data["subject_weights"])],` |
| `location = self.pick_weighted_with_density(valid_locations, scene_density)` | insert `valid_locations = self._apply_taste(valid_locations, "location", taste)` before |
| `environment = self.pick_weighted_with_density(environments, scene_density)` | insert `environments = self._apply_taste(environments, "environment", taste)` before |
| `light_time = self.pick_weighted(time_pool)` | insert `time_pool = self._apply_taste(time_pool, "light_time", taste)` before |
| `light_quality = self.pick_weighted(quality_pool)` | insert `quality_pool = self._apply_taste(quality_pool, "light_quality", taste)` before |
| `mood_entry = self.pick_weighted(mood_pool)` | insert `mood_pool = self._apply_taste(mood_pool, "mood", taste)` before |
| `framing = self.pick_weighted_with_density(valid_framings, scene_density)` | insert `valid_framings = self._apply_taste(valid_framings, "framing", taste)` before |
| `lens = self.pick_weighted(valid_lenses)` | insert `valid_lenses = self._apply_taste(valid_lenses, "lens", taste)` before |
| `camera_angle = self.pick_weighted(boosted_angles)` | insert `boosted_angles = self._apply_taste(boosted_angles, "camera_angle", taste)` before |
| `render_medium = self.pick_weighted(valid_render_stable)` | insert `valid_render_stable = self._apply_taste(valid_render_stable, "render_medium", taste)` before |
| `quality_marker = self.pick_weighted(valid_quality_markers)` | insert `valid_quality_markers = self._apply_taste(valid_quality_markers, "quality_marker", taste)` before |
| `environmental_condition = self.pick_weighted_with_density(` (the 3-line call using `condition_pool`) | insert `condition_pool = self._apply_taste(condition_pool, "environmental_condition", taste)` before |

Theme block (replaces the `theme_name = random.choice(...)` line; keeps today's exact RNG behavior when there is no taste):

```python
        if taste:
            theme_items = self._apply_taste(
                [{"label": name, "weight": 1.0} for name in THEMES],
                "theme",
                taste,
            )
            theme_name = self.pick_weighted(theme_items)["label"]
        else:
            theme_name = random.choice(list(THEMES.keys()))
```

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/generation -v`
Expected: PASS (all, including the original unmodified prompt-engine and context tests).

- [ ] **Step 5: Commit**

```bash
git add generation/prompt_engine.py tests/generation/test_prompt_engine.py
git commit -m "feat: bias PromptEngine trait picks by learned taste multipliers"
```

---

### Task 5: `WallpaperEngine.run(taste=...)`

**Files:**
- Modify: `engine/wallpaper_engine.py`
- Test: `tests/engine/test_wallpaper_engine.py`

**Interfaces:**
- Consumes: `PromptEngine.generate(context=None, taste=None)` (Task 4).
- Produces: `WallpaperEngine.run(context: dict | None = None, taste: dict | None = None) -> CycleResult | None`. `generate()` is called with only the truthy keyword arguments; with neither, it is called with no arguments (old fakes keep working).

- [ ] **Step 1: Write the failing test**

In `tests/engine/test_wallpaper_engine.py`, replace the `ContextPromptEngine` class with:

```python
class ContextPromptEngine:
    def __init__(self):
        self.contexts = []
        self.tastes = []

    def generate(self, context=None, taste=None):
        self.contexts.append(context)
        self.tastes.append(taste)
        return {
            "final_prompt": "a cinematic castle",
            "semantic_prompt": "a castle",
            "dna": {"theme": "fantasy"},
        }
```

and append:

```python
def test_run_passes_taste_to_prompt_engine_only_when_truthy(tmp_path):
    prompt_engine = ContextPromptEngine()
    result = _result(tmp_path)
    engine = _make_engine(
        FakeGPUMonitor([True, True, True]), FakeBackend(result=result), [], prompt_engine=prompt_engine,
    )
    taste = {"mood": {"eerie": 1.5}}

    engine.run(taste=taste)
    engine.run(taste={})
    engine.run()

    assert prompt_engine.tastes == [taste, None, None]
```

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_engine.py -v`
Expected: FAIL — `run() got an unexpected keyword argument 'taste'`.

- [ ] **Step 3: Write minimal implementation**

In `engine/wallpaper_engine.py` change the signature line to:

```python
    def run(self, context: dict | None = None, taste: dict | None = None) -> CycleResult | None:
```

and replace the block

```python
            if context:
                prompt_data = self.prompt_engine.generate(context=context)
            else:
                prompt_data = self.prompt_engine.generate()
```

with:

```python
            hints = {
                name: value
                for name, value in (("context", context), ("taste", taste))
                if value
            }
            prompt_data = self.prompt_engine.generate(**hints)
```

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/engine -v`
Expected: PASS (all, incl. the existing context test and the old no-argument `FakePromptEngine` tests).

- [ ] **Step 5: Commit**

```bash
git add engine/wallpaper_engine.py tests/engine/test_wallpaper_engine.py
git commit -m "feat: pass taste through WallpaperEngine.run to PromptEngine.generate"
```

---

### Task 6: Daemon wiring — record ratings, compute and log taste

**Files:**
- Modify: `engine/wallpaper_daemon.py`
- Test: `tests/engine/test_wallpaper_daemon.py`

**Interfaces:**
- Consumes: `HistoryRepository.set_rating(image_path, rating) -> bool` (Task 2); `compute_taste`, `taste_extremes` (Task 3); `WallpaperEngine.run(context=..., taste=...)` (Task 5).
- Produces: `WallpaperDaemon._compute_taste() -> dict | None` (None on failure or empty taste); `like()`/`dislike()` additionally call `history_repository.set_rating(state["image_path"], ±1)` **before** `seed_pool.rate_current`, best-effort: if `set_rating` raises or returns `False` the problem is logged and `seed_pool.rate_current` is still called.

- [ ] **Step 1: Write the failing tests**

In `tests/engine/test_wallpaper_daemon.py`:

Replace `FakeEngine` and `FakeHistory` with:

```python
class FakeEngine:
    def __init__(self, results=None, fail_first=False):
        self.results = list(results or [])
        self.fail_first = fail_first
        self.contexts = []
        self.tastes = []
        self.runs = 0

    def run(self, context=None, taste=None):
        self.runs += 1
        self.contexts.append(context)
        self.tastes.append(taste)
        if self.fail_first and self.runs == 1:
            raise RuntimeError("bad cycle")
        return self.results.pop(0) if self.results else None


class FakeHistory:
    def __init__(self, entries=(), load_error=None, rating_ok=True, rating_error=None):
        self.entries = list(entries)
        self.load_error = load_error
        self.rating_ok = rating_ok
        self.rating_error = rating_error
        self.ratings = []

    def load(self):
        if self.load_error:
            raise self.load_error
        return self.entries

    def set_rating(self, image_path, rating):
        self.ratings.append((image_path, rating))
        if self.rating_error:
            raise self.rating_error
        return self.rating_ok
```

Append:

```python
# --- taste learning -------------------------------------------------------

def test_like_and_dislike_record_a_rating_on_the_current_image(tmp_path):
    daemon = _daemon(tmp_path, FakeEngine([_cycle(path="wallpapers/new.png")]))
    daemon.run_cycle()

    daemon.like()
    daemon.dislike()

    image = str(Path("wallpapers/new.png"))
    assert daemon.history_repository.ratings == [(image, 1), (image, -1)]
    assert daemon.seed_pool.rated == [([1, 2], True), ([1, 2], False)]


def test_rating_after_revert_records_on_the_reverted_image(tmp_path):
    older, newer = tmp_path / "older.png", tmp_path / "newer.png"
    older.write_bytes(b"x")
    newer.write_bytes(b"x")
    history = FakeHistory([
        {"image_path": str(older), "seeds": [10, 11]},
        {"image_path": str(newer), "seeds": [20, 21]},
    ])
    daemon = _daemon(tmp_path, FakeEngine([_cycle(seeds=(20, 21))]), history=history)
    daemon.run_cycle()

    daemon.revert()
    daemon.like()

    assert history.ratings == [(str(older), 1)]


def test_rating_for_image_missing_from_history_is_logged_and_does_not_crash(tmp_path, caplog):
    import logging

    daemon = _daemon(tmp_path, FakeEngine([_cycle()]), history=FakeHistory(rating_ok=False))
    daemon.run_cycle()

    with caplog.at_level(logging.WARNING):
        daemon.like()

    assert "not found in history" in caplog.text
    assert daemon.seed_pool.rated == [([1, 2], True)]


def test_rating_still_rescores_seeds_when_history_write_raises(tmp_path, caplog):
    import logging

    history = FakeHistory(rating_error=PermissionError("locked"))
    daemon = _daemon(tmp_path, FakeEngine([_cycle()]), history=history)
    daemon.run_cycle()

    with caplog.at_level(logging.ERROR):
        daemon.like()
        daemon.dislike()

    assert daemon.seed_pool.rated == [([1, 2], True), ([1, 2], False)]
    assert "Recording rating in history failed" in caplog.text


def test_rating_without_current_state_records_nothing(tmp_path):
    daemon = _daemon(tmp_path)

    daemon.like()

    assert daemon.history_repository.ratings == []


def test_cycle_passes_taste_computed_from_rated_history(tmp_path):
    history = FakeHistory([
        {"image_path": "a.png", "rating": 1, "dna": {"mood": "eerie"}},
        {"image_path": "b.png", "dna": {"mood": "serene"}},
    ])
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine, history=history)

    daemon.run_cycle()

    assert engine.tastes[0]["mood"]["eerie"] == 1.25
    assert "serene" not in engine.tastes[0]["mood"]


def test_cycle_with_no_ratings_passes_no_taste(tmp_path):
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine, history=FakeHistory([{"image_path": "a.png"}]))

    daemon.run_cycle()

    assert engine.tastes == [None]


def test_cycle_still_runs_when_taste_computation_fails(tmp_path):
    engine = FakeEngine([_cycle()])
    daemon = _daemon(tmp_path, engine, history=FakeHistory(load_error=RuntimeError("corrupt")))

    daemon.run_cycle()

    assert engine.runs == 1
    assert engine.tastes == [None]
    assert daemon.state["seeds"] == [1, 2]


def test_cycle_logs_boosted_and_penalized_taste(tmp_path, caplog):
    import logging

    history = FakeHistory([
        {"image_path": "a.png", "rating": 1, "dna": {"mood": "eerie"}},
        {"image_path": "b.png", "rating": -1, "dna": {"mood": "serene"}},
    ])
    daemon = _daemon(tmp_path, FakeEngine(), history=history)

    with caplog.at_level(logging.INFO):
        daemon.run_cycle()

    assert "Taste boosted: mood=eerie x1.25" in caplog.text
    assert "Taste penalized: mood=serene x0.75" in caplog.text
```

- [ ] **Step 2: Run to verify failure**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_daemon.py -v`
Expected: FAIL — `FakeEngine`/real daemon mismatch: `like()` doesn't call `set_rating` (ratings `== []`); `engine.tastes` stays `[None]` / `KeyError`.

- [ ] **Step 3: Write minimal implementation**

In `engine/wallpaper_daemon.py`:

(a) Add import near the other imports:

```python
from analytics.taste_model import compute_taste, taste_extremes
```

(b) In `run_cycle`, change `result = self.engine.run(context=self.get_context())` to:

```python
            result = self.engine.run(context=self.get_context(), taste=self._compute_taste())
```

(c) Add these two methods directly above `# --- hotkey actions` (before `like`):

```python
    def _compute_taste(self) -> dict | None:
        """Learned trait multipliers from rated history; None if unavailable (never blocks a cycle)."""
        try:
            taste = compute_taste(self.history_repository.load())
        except Exception:
            logging.exception("Taste computation failed, generating without it")
            return None
        self._log_taste(taste)
        return taste or None

    @staticmethod
    def _log_taste(taste: dict) -> None:
        boosted, penalized = taste_extremes(taste)
        if boosted:
            logging.info("Taste boosted: %s", ", ".join(f"{t}={v} x{m:.2f}" for t, v, m in boosted))
        if penalized:
            logging.info("Taste penalized: %s", ", ".join(f"{t}={v} x{m:.2f}" for t, v, m in penalized))
```

(d) In `_rate`, after the `if not state:` guard and before the `rate_current` call, insert (best-effort: a history problem must never stop the seed rescoring that follows):

```python
        rating = 1 if liked else -1
        try:
            if not self.history_repository.set_rating(state["image_path"], rating):
                logging.warning("Rated image not found in history: %s", state["image_path"])
        except Exception:
            logging.exception("Recording rating in history failed")
```

- [ ] **Step 4: Run to verify pass**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_daemon.py -v` (run twice — it uses threads)
Expected: PASS (all, incl. the pre-existing scheduler/revert/quarantine tests).

- [ ] **Step 5: Commit**

```bash
git add engine/wallpaper_daemon.py tests/engine/test_wallpaper_daemon.py
git commit -m "feat: record ratings on history and steer prompts with learned taste in the daemon"
```

---

### Task 7: README note, full suite, manual verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Edit README**

Append under the existing `## Daemon` section:

```markdown
### Taste learning

Likes (`Ctrl+Alt+Up`) and dislikes (`Ctrl+Alt+Down`) are recorded on the rated image's history entry.
Each cycle, traits (theme, mood, lighting, framing, ...) you rate well get a gentle weight boost and
traits you rate poorly a gentle penalty (bounded to `TASTE_MIN`..`TASTE_MAX`, shrunk toward neutral when
you have few ratings, never excluded). The log shows `Taste boosted: ...` / `Taste penalized: ...` lines.
```

- [ ] **Step 2: Run the full suite**

Run: `"C:\Python313\python.exe" -m pytest -q`
Expected: all pass (`test_trait_averages` now passes too — baseline failure fixed in Task 1).

- [ ] **Step 3: Import smoke check**

Run: `"C:\Python313\python.exe" -c "import main; d = main.build_daemon(); print(d._compute_taste())"`
Expected: prints `None` (no ratings yet) or a taste dict; no traceback.

- [ ] **Step 4: Manual verification (needs real GPU/ComfyUI/desktop)**

Run `"C:\Python313\python.exe" main.py` and:
1. `Ctrl+Alt+Right` to generate a wallpaper; press `Ctrl+Alt+Up`. Open `data/history.json`: the newest entry has `"rating": 1`. Press `Ctrl+Alt+Up` again: still `1` (not doubled).
2. Press `Ctrl+Alt+Down`: that entry's rating becomes `-1`.
3. Generate and rate 5–10 wallpapers (mix of likes/dislikes), restart the daemon, press `Ctrl+Alt+Right`: the log shows `Taste boosted: ...` and `Taste penalized: ...` naming traits from what you rated.
4. Generate ~10 more; confirm boosted traits appear more often in `history.json` `dna` than before, but variety remains.
5. Corrupt-history check: with the daemon stopped, rename `data/history.json` to a backup and write `not json` to it, start the daemon, `Ctrl+Alt+Right`: log shows `Taste computation failed`, the wallpaper still generates (note: the corrupt file is moved to `history.corrupt` by the repository; restore your backup afterwards).

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: document taste learning"
```

---

## Self-Review

**Spec coverage:** rating storage + idempotency + not-found + `RLock` → T2; `compute_taste` math, constants, malformed handling, no-decay note → T1/T3; `taste_extremes` for the daemon's boosted/penalized logging → T3/T6; `PromptEngine` hooks (theme weighted, subject parallel weights, all 13 traits) + no-op when empty + hard-filters-first ordering → T4; engine passthrough only when truthy → T5; daemon `set_rating` + `rate_current` kept, taste each cycle, failure → `None`, logging → T6; `GeneAnalytics` fixture fix → T1; README/manual → T7. Non-goals (preference model, Thompson sampling, decay, UI, weather/tray) not built.

**Placeholder scan:** none; every code step has literal code; the T4 edit table gives exact find strings and replacement lines.

**Type consistency:** taste shape `{trait: {value: float}}` is identical across `compute_taste` (T3), `_apply_taste`/`_taste_multiplier` (T4), `engine.run(taste=)` (T5), and the daemon (T6); `set_rating(image_path: str, rating: int) -> bool` matches the `FakeHistory.set_rating` in T6; `taste_extremes` returns `(trait, value, multiplier)` tuples consumed by `_log_taste`; `PromptEngine.TASTE_TRAITS` names equal the `dna` keys produced in `generate` (guarded by T4's spy test).

**Review Focus coverage:** items 1→T4 spy test; 2→T2 idempotence/not-found/invalid-rating tests + T6 best-effort test; 3→T3 1-like/1-dislike/floor tests; 4→T6 `load_error` test; 5→T2 concurrency test; 6→T3 malformed-record/dna/trait/rating tests; 7→T4 `pick_weighted_with_density` behavioral test.

**Revision pass (review findings):** `compute_taste` hardened against malformed history (T3); history rating made best-effort in the daemon (T6); `set_rating` validates `±1` (T2); added a non-theme `pick_weighted_with_density` steering test (T4); taste ordering clarified (Architecture, Global Constraints, T4). No scope added.
