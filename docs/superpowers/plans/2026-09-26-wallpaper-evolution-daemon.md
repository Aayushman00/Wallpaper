# Wallpaper Evolution Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `main.py` into a resident daemon that auto-generates wallpapers on a timer, takes like/dislike/next/revert global hotkeys, actually mutates reused seeds (with lineage tracking), and adds a quality floor, focus-assist gate, and time/season-aware prompting.

**Architecture:** `WallpaperDaemon` (new, `engine/wallpaper_daemon.py`) owns a scheduler thread that loops `engine.run()` and a hotkey thread running a Win32 message pump. `WallpaperEngine.run()` keeps its one-cycle behavior but now returns a `CycleResult` (or `None`) so the daemon knows what is displayed, and quarantines images below `AESTHETIC_QUALITY_FLOOR`. `SeedPool.next_seed()` returns `(seed, parent_seed, generation)` and `record_result` accepts optional lineage; `rate_current`/`penalize` re-score stored records under a lock shared by all `SeedPool` methods. Win32 access (`system/hotkeys.py`, `system/focus_assist.py`) takes an injectable `user32` so the logic is unit-testable with fakes.

**Tech Stack:** Python 3.13, pytest, `ctypes` against `user32`/`kernel32` (stdlib). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-26-wallpaper-evolution-daemon-design.md`

## Global Constraints

- Local Windows side project — no Protocol/ABC interfaces for single-implementation boundaries.
- No new dependencies. Hotkeys and fullscreen detection go through `ctypes`/`user32`, like `system/wallpaper.py`.
- Preserve `WallpaperEngine.run()`'s one-cycle behavior and its existing tests (`tests/engine/test_wallpaper_engine.py`). Existing tests may only be edited where a signature the spec explicitly changes forces it (called out per task).
- `SeedPool.record_result`'s existing positional signature `(seeds, score, prompt, theme)` and top-`BEST_SEED_LIMIT` ranking stay; `lineage` is a new trailing optional keyword; `parent_seed`/`generation` are additive record fields.
- `PromptEngine.generate()` with no arguments behaves exactly as today; `tests/generation/test_prompt_engine.py` passes unmodified.
- Test runner: `"C:\Python313\python.exe" -m pytest <path> -v`.
- Baseline: `tests/test_gene_analytics.py::test_trait_averages` already fails on main — out of scope, do not fix.
- No `__init__.py` files anywhere (namespace packages). Test file basenames must be unique across `tests/` (no `__init__.py`, rootdir import mode): new tests use `test_context_signals.py`, `test_focus_assist.py`, `test_hotkeys.py`, `test_wallpaper_daemon.py`.
- Constants (exact values from spec): `AESTHETIC_QUALITY_FLOOR = 4.0`, `FOCUS_ASSIST_RECHECK_SECONDS = 300`, `SEED_RATING_LIKE_MULTIPLIER = 1.5`, `SEED_RATING_DISLIKE_MULTIPLIER = 0.3`, `GENERATION_INTERVAL_SECONDS = 14400` (spec: user preference, default suggestion 4 h — confirm at review).
- Hotkeys: `Ctrl+Alt+Up` like, `Ctrl+Alt+Down` dislike, `Ctrl+Alt+Right` generate-next (bypasses focus-assist), `Ctrl+Alt+Left` revert.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

Spec-listed items (quarantine leaves `current_state` untouched, `next_seed` return-type ripple, focus-assist fails open, daemon survives a bad cycle) are pinned in Tasks 2, 5, 6, 8. Additional inputs the spec implies but doesn't test, most likely first:

1. **Mutated seed leaves the valid range** — a parent seed near 0 plus a negative offset gives a negative seed (ComfyUI rejects it); near `2**63-1` overflows. Expected: clamped to `[0, 2**63-1]`. Pinned in Task 2.
2. **Desktop/shell focused counts as "fullscreen"** — the shell window's rect covers the whole screen, so naive rect-vs-screen comparison would defer generation forever while the user sits on the desktop. Expected: desktop/shell foreground → not fullscreen. Pinned in Task 6.
3. **Hotkey rating races a running cycle on `best_seeds.json`** — the hotkey thread's read-modify-write and the scheduler's `record_result` interleave, losing a record (or hitting a Windows `PermissionError` on `replace`). Expected: no lost updates. Pinned in Task 3.
4. **Legacy `best_seeds.json` records without `parent_seed`/`generation`** — existing user data has neither field; `next_seed` must not `KeyError`. Expected: treated as generation 0. Pinned in Task 2.
5. **Revert target image deleted/moved** — history keeps an `image_path` whose file may no longer exist. Expected: log and no-op, hotkey thread survives. Pinned in Task 8.

---

### Task 1: Settings constants and state-file path

**Files:**
- Modify: `config/settings.py`
- Modify: `config/paths.py`
- Test: `tests/config/test_settings.py`

**Interfaces:**
- Produces: `settings.GENERATION_INTERVAL_SECONDS`, `settings.AESTHETIC_QUALITY_FLOOR`, `settings.FOCUS_ASSIST_RECHECK_SECONDS`, `settings.SEED_RATING_LIKE_MULTIPLIER`, `settings.SEED_RATING_DISLIKE_MULTIPLIER`; `paths.CURRENT_STATE_FILE: Path`.

- [ ] **Step 1: Write the failing test**

Append to `tests/config/test_settings.py`:

```python
def test_daemon_constants_present_and_correct():
    assert settings.GENERATION_INTERVAL_SECONDS == 14400
    assert settings.AESTHETIC_QUALITY_FLOOR == 4.0
    assert settings.FOCUS_ASSIST_RECHECK_SECONDS == 300
    assert settings.SEED_RATING_LIKE_MULTIPLIER == 1.5
    assert settings.SEED_RATING_DISLIKE_MULTIPLIER == 0.3


def test_current_state_file_lives_in_data_dir():
    from config.paths import CURRENT_STATE_FILE, DATA_DIR

    assert CURRENT_STATE_FILE == DATA_DIR / "current_state.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py -v`
Expected: FAIL with `AttributeError: module 'config.settings' has no attribute 'GENERATION_INTERVAL_SECONDS'` (and ImportError for `CURRENT_STATE_FILE`).

- [ ] **Step 3: Write minimal implementation**

Append to `config/settings.py`:

```python
GENERATION_INTERVAL_SECONDS = 14400
AESTHETIC_QUALITY_FLOOR = 4.0
FOCUS_ASSIST_RECHECK_SECONDS = 300
SEED_RATING_LIKE_MULTIPLIER = 1.5
SEED_RATING_DISLIKE_MULTIPLIER = 0.3
```

In `config/paths.py`, after the `BEST_SEEDS_FILE` line add:

```python
CURRENT_STATE_FILE = DATA_DIR / "current_state.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add config/settings.py config/paths.py tests/config/test_settings.py
git commit -m "feat: add daemon settings constants and current_state path"
```

---

### Task 2: Seed mutation and lineage plumbing (SeedPool → WorkflowManager → ComfyBackend → engine)

One task because changing `next_seed()`'s return type breaks every caller; they must change together.

**Files:**
- Modify: `engine/models.py`
- Modify: `engine/seed_pool.py`
- Modify: `generation/comfy/workflow.py` (docstring + `prepare`, lines ~25-30 and ~133-215)
- Modify: `generation/comfy/backend.py` (`generate`)
- Modify: `engine/wallpaper_engine.py` (pass `lineage` to `record_result` — one line)
- Test: `tests/engine/test_models.py`, `tests/engine/test_seed_pool.py`, `tests/generation/comfy/test_workflow.py`, `tests/generation/comfy/test_backend.py`, `tests/engine/test_wallpaper_engine.py`

**Interfaces:**
- Produces:
  - `GenerationResult.used_lineage: list[tuple[int | None, int]]` (default `[]`) — one `(parent_seed, generation)` per entry of `used_seeds`.
  - `SeedPool.next_seed() -> tuple[int, int | None, int]` = `(seed, parent_seed, generation)`; fresh seeds return `(seed, None, 0)`.
  - `SeedPool.record_result(seeds, score, prompt, theme, lineage=None)`.
  - `WorkflowManager.prepare(final_prompt, dna) -> tuple[dict, list[int], list[tuple[int | None, int]]]`.

- [ ] **Step 1: Write the failing tests**

`tests/engine/test_models.py` — append:

```python
def test_generation_result_lineage_defaults_to_empty_and_is_settable():
    plain = GenerationResult(image_path=Path("a.png"), used_seeds=[1], generation_time_seconds=1.0)
    assert plain.used_lineage == []

    with_lineage = GenerationResult(
        image_path=Path("a.png"),
        used_seeds=[1, 2],
        generation_time_seconds=1.0,
        used_lineage=[(None, 0), (99, 3)],
    )
    assert with_lineage.used_lineage == [(None, 0), (99, 3)]
```

`tests/engine/test_seed_pool.py` — replace the whole file with:

```python
from config.settings import BEST_SEED_MUTATION_RANGE
from database.seeds import SeedRepository
from engine.seed_pool import SeedPool


def _record(seed, score=0.9, generation=0, parent_seed=None):
    return {
        "seed": seed,
        "score": score,
        "sampler_index": 0,
        "prompt": "p",
        "theme": "t",
        "parent_seed": parent_seed,
        "generation": generation,
    }


def test_next_seed_fresh_returns_seed_none_zero(tmp_path):
    pool = SeedPool(SeedRepository(tmp_path / "seeds.json"))

    seed, parent_seed, generation = pool.next_seed()

    assert isinstance(seed, int)
    assert parent_seed is None
    assert generation == 0


def test_next_seed_reuse_mutates_within_range_and_tracks_lineage(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(1_000_000, generation=2)])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)  # always reuse

    for _ in range(50):
        seed, parent_seed, generation = pool.next_seed()
        assert abs(seed - 1_000_000) <= BEST_SEED_MUTATION_RANGE
        assert parent_seed == 1_000_000
        assert generation == 3


def test_next_seed_clamps_mutated_seed_to_valid_range(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(10)])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)
    monkeypatch.setattr("engine.seed_pool.random.randint", lambda a, b: -BEST_SEED_MUTATION_RANGE)

    seed, parent_seed, _ = pool.next_seed()
    assert seed == 0
    assert parent_seed == 10

    repo.save([_record(2**63 - 1)])
    monkeypatch.setattr("engine.seed_pool.random.randint", lambda a, b: BEST_SEED_MUTATION_RANGE)
    seed, _, _ = pool.next_seed()
    assert seed == 2**63 - 1


def test_next_seed_tolerates_legacy_records_without_lineage_fields(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([{"seed": 5000, "score": 0.9, "sampler_index": 0, "prompt": "p", "theme": "t"}])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)

    seed, parent_seed, generation = pool.next_seed()

    assert parent_seed == 5000
    assert generation == 1


def test_record_result_persists_ranked_by_score(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111, 222], score=0.9, prompt="a cat", theme="fantasy")
    pool.record_result(seeds=[333], score=0.1, prompt="a dog", theme="space")

    records = repo.load()
    assert len(records) == 3
    assert records[0]["score"] == 0.9
    assert records[-1]["score"] == 0.1


def test_record_result_defaults_lineage_when_omitted(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111], score=0.5, prompt="p", theme="t")

    record = repo.load()[0]
    assert record["parent_seed"] is None
    assert record["generation"] == 0


def test_record_result_stores_lineage_per_seed(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(
        seeds=[111, 222], score=0.5, prompt="p", theme="t",
        lineage=[(None, 0), (99, 3)],
    )

    by_seed = {r["seed"]: r for r in repo.load()}
    assert by_seed[111]["parent_seed"] is None
    assert by_seed[111]["generation"] == 0
    assert by_seed[222]["parent_seed"] == 99
    assert by_seed[222]["generation"] == 3
```

`tests/generation/comfy/test_workflow.py` — replace `FakeSeedPool` and update the two assertions:

```python
class FakeSeedPool:
    def __init__(self, seeds):
        self._seeds = iter(seeds)
        self.calls = 0

    def next_seed(self):
        self.calls += 1
        return next(self._seeds)
```
(unchanged class body, but the passed lists become tuples:)

In `test_prepare_pulls_one_seed_per_ksampler_and_injects_prompt` change to:

```python
    seeds = FakeSeedPool([(111, None, 0), (222, 111, 4)])

    manager = WorkflowManager(workflow_path, seeds)
    workflow, used_seeds, used_lineage = manager.prepare(
        final_prompt="a cinematic castle",
        dna={"theme": "fantasy", "scene_density_score": 5, "subject_type": "structure", "mood": "mythic and ancient"},
    )

    assert seeds.calls == 2
    assert used_seeds == [111, 222]
    assert used_lineage == [(None, 0), (111, 4)]
    assert workflow["6"]["inputs"]["text"] == "a cinematic castle"
    assert workflow["8"]["inputs"]["seed"] == 111
    assert workflow["17"]["inputs"]["seed"] == 222
```

and in `test_prepare_raises_when_no_ksampler_present` change `FakeSeedPool([111])` to `FakeSeedPool([(111, None, 0)])`.

`tests/generation/comfy/test_backend.py` — change `FakeWorkflowManager.prepare` to:

```python
    def prepare(self, final_prompt, dna):
        return {"workflow": "payload"}, [42, 43], [(None, 0), (7, 2)]
```
and in `test_generate_returns_generation_result_on_success` add after the `used_seeds` assert:

```python
    assert result.used_lineage == [(None, 0), (7, 2)]
```

`tests/engine/test_wallpaper_engine.py` — change `FakeSeedPool` to:

```python
class FakeSeedPool:
    def __init__(self):
        self.recorded = []
        self.recorded_lineage = []

    def record_result(self, seeds, score, prompt, theme, lineage=None):
        self.recorded.append((seeds, score, prompt, theme))
        self.recorded_lineage.append(lineage)
```
and in `test_run_happy_path_scores_persists_and_sets_wallpaper`, add `used_lineage=[(None, 0), (41, 2)],` to the `GenerationResult(...)` and, at the end of the test:

```python
    assert engine.seed_pool.recorded_lineage == [[(None, 0), (41, 2)]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Python313\python.exe" -m pytest tests/engine tests/generation/comfy -v`
Expected: FAIL — `TypeError ... unexpected keyword argument 'used_lineage'`, `next_seed()` returns an `int` (cannot unpack), `prepare` returns 2 values.

- [ ] **Step 3: Write minimal implementation**

`engine/models.py` — change imports and `GenerationResult`:

```python
from dataclasses import dataclass, field
from pathlib import Path
```
```python
@dataclass
class GenerationResult:
    image_path: Path
    used_seeds: list[int]
    generation_time_seconds: float
    used_lineage: list[tuple[int | None, int]] = field(default_factory=list)
```

`engine/seed_pool.py` — replace `next_seed` and `record_result`:

```python
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
```
and change the imports/top of file:

```python
from config.settings import (
    BEST_SEED_LIMIT,
    BEST_SEED_MUTATION_RANGE,
    BEST_SEED_REUSE_PROBABILITY,
)
from database.seeds import SeedRepository

MAX_SEED = 2**63 - 1
```

`generation/comfy/workflow.py`:
- Class docstring: ``...exposing `.next_seed() -> (seed, parent_seed, generation)` — duck-typed...``
- `prepare` return annotation → `tuple[dict[str, Any], list[int], list[tuple[int | None, int]]]`.
- After `used_seeds: list[int] = []` add `used_lineage: list[tuple[int | None, int]] = []`.
- Replace `seed = self.seeds.next_seed()` with:
  ```python
                  seed, parent_seed, generation = self.seeds.next_seed()
  ```
  and after `used_seeds.append(seed)` add `used_lineage.append((parent_seed, generation))`.
- Final line: `return workflow, used_seeds, used_lineage`.

`generation/comfy/backend.py`:

```python
        workflow, used_seeds, used_lineage = self.workflow.prepare(request.prompt, request.dna)
```
and in the returned `GenerationResult(...)` add `used_lineage=used_lineage,`.

`engine/wallpaper_engine.py` — in the `record_result(...)` call add `lineage=result.used_lineage,` after `theme=...`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"C:\Python313\python.exe" -m pytest tests/engine tests/generation -v`
Expected: PASS (all). Then full suite: `"C:\Python313\python.exe" -m pytest -q` — only the baseline `test_trait_averages` failure remains.

- [ ] **Step 5: Commit**

```bash
git add engine generation tests
git commit -m "feat: mutate reused seeds and track parent/generation lineage"
```

---

### Task 3: SeedPool `rate_current` / `penalize` with thread-safe access

**Files:**
- Modify: `engine/seed_pool.py`
- Test: `tests/engine/test_seed_pool.py`

**Interfaces:**
- Consumes: `SeedPool` from Task 2 (`record_result`, `next_seed`, `repository`).
- Produces: `SeedPool.rate_current(seeds: list[int], liked: bool) -> None`, `SeedPool.penalize(seeds: list[int]) -> None`; `SeedPool._lock` (`threading.Lock`) guarding every method that touches the repository.

- [ ] **Step 1: Write the failing tests**

Append to `tests/engine/test_seed_pool.py`:

```python
import threading

from config.settings import SEED_RATING_DISLIKE_MULTIPLIER, SEED_RATING_LIKE_MULTIPLIER


def _seeded_pool(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(1, score=0.5), _record(2, score=0.4), _record(3, score=0.3)])
    return repo, SeedPool(repo)


def test_rate_current_like_multiplies_only_matching_seeds(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.rate_current([1, 2], liked=True)

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[1] == 0.5 * SEED_RATING_LIKE_MULTIPLIER
    assert scores[2] == 0.4 * SEED_RATING_LIKE_MULTIPLIER
    assert scores[3] == 0.3


def test_rate_current_dislike_uses_dislike_multiplier(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.rate_current([3], liked=False)

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[3] == 0.3 * SEED_RATING_DISLIKE_MULTIPLIER
    assert scores[1] == 0.5


def test_rate_current_with_unknown_seed_leaves_records_unchanged(tmp_path):
    repo, pool = _seeded_pool(tmp_path)
    before = repo.load()

    pool.rate_current([999], liked=True)

    assert repo.load() == before


def test_penalize_zeroes_matching_seeds_only(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.penalize([1])

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[1] == 0.0
    assert scores[2] == 0.4


def test_concurrent_record_and_rate_do_not_lose_updates(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(0, score=0.5)])
    pool = SeedPool(repo)

    def record(i):
        pool.record_result(seeds=[i], score=0.1, prompt="p", theme="t")

    def rate():
        for _ in range(20):
            pool.rate_current([0], liked=True)

    threads = [threading.Thread(target=record, args=(i,)) for i in range(1, 21)]
    threads.append(threading.Thread(target=rate))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert {r["seed"] for r in repo.load()} == set(range(0, 21))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_seed_pool.py -v`
Expected: FAIL with `AttributeError: 'SeedPool' object has no attribute 'rate_current'` / `'penalize'`.

- [ ] **Step 3: Write minimal implementation**

In `engine/seed_pool.py`: add `import threading`, extend the settings import with `SEED_RATING_DISLIKE_MULTIPLIER, SEED_RATING_LIKE_MULTIPLIER`, and:

```python
    def __init__(self, repository: SeedRepository) -> None:
        self.repository = repository
        self._lock = threading.Lock()
```

Wrap the bodies of `next_seed` and `record_result` in `with self._lock:` (for `next_seed`, lock only the `data = self.repository.load()` line; the rest needs no lock). For `record_result`, lock from `data = self.repository.load()` through `self.repository.save(ranked)`.

Add the new methods:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_seed_pool.py -v`
Expected: PASS (all, incl. the concurrency test).

- [ ] **Step 5: Commit**

```bash
git add engine/seed_pool.py tests/engine/test_seed_pool.py
git commit -m "feat: add SeedPool.rate_current/penalize with a shared repository lock"
```

---

### Task 4: Context signals and context-aware lighting bias

**Files:**
- Create: `generation/context_signals.py`
- Modify: `generation/prompt_engine.py` (`generate` signature ~line 163; time-pool block ~lines 215-228; add class attrs + helper)
- Test: `tests/generation/test_context_signals.py` (new), `tests/generation/test_prompt_engine.py`

**Interfaces:**
- Produces:
  - `get_time_of_day(now: datetime | None = None) -> str` (`"morning"` 05–11, `"afternoon"` 12–16, `"evening"` 17–20, `"night"` 21–04).
  - `get_season(now: datetime | None = None) -> str` (Northern Hemisphere: Dec–Feb winter, Mar–May spring, Jun–Aug summer, Sep–Nov autumn).
  - `get_context(now: datetime | None = None) -> dict[str, str]` = `{"time_of_day": ..., "season": ...}`.
  - `PromptEngine.generate(context: dict | None = None)`; `PromptEngine._bias_lighting_for_context(pool, context) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

`tests/generation/test_context_signals.py`:

```python
from datetime import datetime

import pytest

from generation.context_signals import get_context, get_season, get_time_of_day


@pytest.mark.parametrize("hour,expected", [
    (0, "night"), (4, "night"), (5, "morning"), (11, "morning"),
    (12, "afternoon"), (16, "afternoon"), (17, "evening"), (20, "evening"),
    (21, "night"), (23, "night"),
])
def test_time_of_day_boundaries(hour, expected):
    assert get_time_of_day(datetime(2026, 6, 15, hour, 30)) == expected


@pytest.mark.parametrize("month,expected", [
    (12, "winter"), (1, "winter"), (2, "winter"),
    (3, "spring"), (5, "spring"),
    (6, "summer"), (8, "summer"),
    (9, "autumn"), (11, "autumn"),
])
def test_season_boundaries(month, expected):
    assert get_season(datetime(2026, month, 15, 12)) == expected


def test_get_context_combines_both_signals():
    assert get_context(datetime(2026, 12, 25, 22)) == {"time_of_day": "night", "season": "winter"}


def test_signals_default_to_the_system_clock():
    assert get_time_of_day() in {"morning", "afternoon", "evening", "night"}
    assert get_season() in {"winter", "spring", "summer", "autumn"}
```

Append to `tests/generation/test_prompt_engine.py`:

```python
POOL = [
    {"label": "golden hour", "weight": 0.2},
    {"label": "harsh noon", "weight": 0.2},
    {"label": "full dark", "weight": 0.2},
]


def test_generate_accepts_context_and_still_returns_expected_shape():
    result = PromptEngine().generate(context={"time_of_day": "night", "season": "winter"})

    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES


def test_bias_boosts_context_matching_lighting_without_filtering():
    biased = PromptEngine()._bias_lighting_for_context(POOL, {"time_of_day": "night", "season": "autumn"})

    weights = {item["label"]: item["weight"] for item in biased}
    assert weights["full dark"] > 0.2        # night favours full dark
    assert weights["golden hour"] > 0.2      # autumn favours golden hour
    assert weights["harsh noon"] == 0.2      # untouched
    assert len(biased) == len(POOL)          # soft bias, never a filter


def test_bias_does_not_mutate_input_pool():
    PromptEngine()._bias_lighting_for_context(POOL, {"time_of_day": "night"})

    assert [item["weight"] for item in POOL] == [0.2, 0.2, 0.2]


def test_bias_is_a_noop_without_or_with_unknown_context():
    engine = PromptEngine()

    assert engine._bias_lighting_for_context(POOL, None) == POOL
    assert engine._bias_lighting_for_context(POOL, {}) == POOL
    assert engine._bias_lighting_for_context(POOL, {"time_of_day": "teatime"}) == POOL
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/test_context_signals.py tests/generation/test_prompt_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generation.context_signals'`; `generate() got an unexpected keyword argument 'context'`.

- [ ] **Step 3: Write minimal implementation**

`generation/context_signals.py`:

```python
"""Time-of-day and season signals used to nudge prompt generation."""

from __future__ import annotations

from datetime import datetime


def get_time_of_day(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def get_season(now: datetime | None = None) -> str:
    # ponytail: Northern Hemisphere only, add a hemisphere setting if that ever matters
    month = (now or datetime.now()).month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def get_context(now: datetime | None = None) -> dict[str, str]:
    now = now or datetime.now()
    return {"time_of_day": get_time_of_day(now), "season": get_season(now)}
```

`generation/prompt_engine.py` — add inside `PromptEngine`, directly above `# Main generation entry point`:

```python
    # -------------------------------------------------------------------------
    # Context-aware lighting bias — soft nudge, never a filter
    # -------------------------------------------------------------------------

    CONTEXT_BIAS_MULTIPLIER = 3.0

    _CONTEXT_LIGHT_BIAS = {
        "morning":   {"pre-dawn blue hour", "golden hour"},
        "afternoon": {"harsh noon", "deep overcast midday", "flat grey diffuse"},
        "evening":   {"golden hour", "twilight"},
        "night":     {"full dark", "twilight", "pre-dawn blue hour"},
        "winter":    {"flat grey diffuse", "deep overcast midday", "pre-dawn blue hour"},
        "spring":    {"golden hour", "pre-dawn blue hour"},
        "summer":    {"harsh noon", "golden hour"},
        "autumn":    {"golden hour", "twilight"},
    }

    def _bias_lighting_for_context(
        self,
        pool: list[dict],
        context: dict | None,
    ) -> list[dict]:
        if not context:
            return pool
        favored: set[str] = set()
        for key in ("time_of_day", "season"):
            favored |= self._CONTEXT_LIGHT_BIAS.get(context.get(key), set())
        if not favored:
            return pool
        return [
            {**item, "weight": item["weight"] * self.CONTEXT_BIAS_MULTIPLIER}
            if item["label"] in favored else item
            for item in pool
        ]
```

Change the signature `def generate(self) -> dict[str, object]:` to `def generate(self, context: dict | None = None) -> dict[str, object]:`, and after the `time_pool = self._diversity.apply_decay(category="light_time", ...)` statement add:

```python
        time_pool = self._bias_lighting_for_context(time_pool, context)
```
(Space theme's `space_only` labels are not in the bias table, so space is naturally unaffected.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `"C:\Python313\python.exe" -m pytest tests/generation -v`
Expected: PASS (all, including the unmodified original `test_generate_returns_expected_shape`).

- [ ] **Step 5: Commit**

```bash
git add generation tests/generation
git commit -m "feat: add time-of-day/season context signals and soft lighting bias"
```

---

### Task 5: Quality floor, quarantine, context pass-through, `CycleResult`

**Files:**
- Modify: `engine/models.py` (add `CycleResult`)
- Modify: `database/history.py` (`append` gains `quarantined`)
- Modify: `engine/wallpaper_engine.py` (`run`)
- Test: `tests/engine/test_wallpaper_engine.py`, `tests/engine/test_models.py`, `tests/test_history.py`

**Interfaces:**
- Consumes: `SeedPool.penalize` (Task 3), `GenerationResult.used_lineage` (Task 2), `AESTHETIC_QUALITY_FLOOR` (Task 1), `PromptEngine.generate(context=...)` (Task 4).
- Produces:
  - `CycleResult(image_path: Path, used_seeds: list[int], generation: int, quarantined: bool = False)` in `engine/models.py`.
  - `WallpaperEngine.run(context: dict | None = None) -> CycleResult | None` — `None` when the cycle was skipped/aborted; `generation` = max generation over `used_lineage` (0 if empty).
  - `HistoryRepository.append(..., quarantined: bool = False)` — writes `"quarantined": true` only when true.

- [ ] **Step 1: Write the failing tests**

`tests/engine/test_models.py` — append:

```python
def test_cycle_result_defaults_to_not_quarantined():
    from engine.models import CycleResult

    result = CycleResult(image_path=Path("a.png"), used_seeds=[1, 2], generation=3)
    assert result.generation == 3
    assert result.quarantined is False
```

`tests/test_history.py` — append:

```python
def _append(repo, **extra):
    repo.append(
        seeds=[1], semantic_score=50.0, aesthetic_score=5.0, combined_score=0.5,
        image_path="a.png", generation_time=1.0, semantic_prompt="p", dna={}, **extra,
    )


def test_history_quarantined_flag_only_written_when_true(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")

    _append(repo)
    _append(repo, quarantined=True)

    normal, quarantined = repo.load()
    assert "quarantined" not in normal
    assert quarantined["quarantined"] is True
```

`tests/engine/test_wallpaper_engine.py` — edits:

1. Add `penalize` to `FakeSeedPool` (and a `penalized` list):

```python
class FakeSeedPool:
    def __init__(self):
        self.recorded = []
        self.recorded_lineage = []
        self.penalized = []

    def record_result(self, seeds, score, prompt, theme, lineage=None):
        self.recorded.append((seeds, score, prompt, theme))
        self.recorded_lineage.append(lineage)

    def penalize(self, seeds):
        self.penalized.append(seeds)
```

2. Add a context-aware fake prompt engine below `FakePromptEngine`:

```python
class ContextPromptEngine:
    def __init__(self):
        self.contexts = []

    def generate(self, context=None):
        self.contexts.append(context)
        return {
            "final_prompt": "a cinematic castle",
            "semantic_prompt": "a castle",
            "dna": {"theme": "fantasy"},
        }
```

3. Give `_make_engine` two optional parameters (existing callers unaffected):

```python
def _make_engine(gpu_monitor, backend, evaluator_factories_called, aesthetic=6.0, prompt_engine=None):
```
with `return 6.0` in `aesthetic_factory` becoming `return aesthetic`, and `prompt_engine=prompt_engine or FakePromptEngine(),` in the `WallpaperEngine(...)` call.

4. Append the new tests:

```python
def _result(tmp_path, lineage=None):
    return GenerationResult(
        image_path=tmp_path / "wallpapers" / "out.png",
        used_seeds=[42, 43],
        generation_time_seconds=1.5,
        used_lineage=lineage if lineage is not None else [(None, 0), (41, 2)],
    )


def test_run_returns_none_when_cycle_is_skipped():
    engine = _make_engine(FakeGPUMonitor([False] * 5), FakeBackend(), [])

    assert engine.run() is None


def test_run_returns_cycle_result_with_max_generation(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [])

    cycle = engine.run()

    assert cycle.image_path == result.image_path
    assert cycle.used_seeds == [42, 43]
    assert cycle.generation == 2
    assert cycle.quarantined is False


def test_run_quarantines_image_below_quality_floor(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [], aesthetic=3.9)

    cycle = engine.run()

    assert cycle.quarantined is True
    assert engine.seed_pool.penalized == [[42, 43]]
    assert engine.seed_pool.recorded == []
    assert engine.wallpaper_service.set_calls == []
    assert engine.history_repository.appended[0]["quarantined"] is True


def test_run_does_not_quarantine_at_exactly_the_floor(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [], aesthetic=4.0)

    cycle = engine.run()

    assert cycle.quarantined is False
    assert engine.wallpaper_service.set_calls == [result.image_path]
    assert engine.history_repository.appended[0]["quarantined"] is False


def test_run_passes_context_to_prompt_engine_only_when_given(tmp_path):
    prompt_engine = ContextPromptEngine()
    result = _result(tmp_path)
    engine = _make_engine(
        FakeGPUMonitor([True, True]), FakeBackend(result=result), [], prompt_engine=prompt_engine,
    )

    engine.run(context={"time_of_day": "night"})
    engine.run()

    assert prompt_engine.contexts == [{"time_of_day": "night"}, None]
```
(The second `engine.run()` with no context calls `generate()` with no arguments, which `ContextPromptEngine` records as `None`; the original `FakePromptEngine.generate()` takes no args, so the engine must not pass `context=None` — pinned by every pre-existing test.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Python313\python.exe" -m pytest tests/engine tests/test_history.py -v`
Expected: FAIL — `ImportError: cannot import name 'CycleResult'`; `append() got an unexpected keyword argument 'quarantined'`; `run() got an unexpected keyword argument 'context'`.

- [ ] **Step 3: Write minimal implementation**

`engine/models.py` — append:

```python
@dataclass
class CycleResult:
    image_path: Path
    used_seeds: list[int]
    generation: int
    quarantined: bool = False
```

`database/history.py` — add `quarantined: bool = False,` as the last parameter of `append` and, after the `records.append({...})` call:

```python
        if quarantined:
            records[-1]["quarantined"] = True
```

`engine/wallpaper_engine.py`:
- imports: `from config.settings import AESTHETIC_QUALITY_FLOOR, GPU_IDLE_RETRIES, GPU_IDLE_WAIT_SECONDS` and `from engine.models import CycleResult, GenerationRequest`.
- Signature: `def run(self, context: dict | None = None) -> CycleResult | None:`; every existing bare `return` stays (returns `None`).
- Replace `prompt_data = self.prompt_engine.generate()` with:

```python
            if context:
                prompt_data = self.prompt_engine.generate(context=context)
            else:
                prompt_data = self.prompt_engine.generate()
```
- After `logging.info("Combined Score: %.2f", combined_score)`, replace the history/record/set block with:

```python
            quarantined = aesthetic_score < AESTHETIC_QUALITY_FLOOR
            generation = max((g for _, g in result.used_lineage), default=0)

            self.history_repository.append(
                seeds=result.used_seeds,
                semantic_score=semantic_score,
                aesthetic_score=aesthetic_score,
                combined_score=combined_score,
                image_path=str(result.image_path),
                generation_time=result.generation_time_seconds,
                semantic_prompt=prompt_data["semantic_prompt"],
                dna=prompt_data["dna"],
                quarantined=quarantined,
            )

            if quarantined:
                logging.warning(
                    "Aesthetic score %.2f below floor %.2f, quarantining image",
                    aesthetic_score, AESTHETIC_QUALITY_FLOOR,
                )
                self.seed_pool.penalize(result.used_seeds)
                return CycleResult(result.image_path, result.used_seeds, generation, quarantined=True)

            self.seed_pool.record_result(
                seeds=result.used_seeds,
                score=combined_score,
                prompt=request.prompt,
                theme=prompt_data["dna"]["theme"],
                lineage=result.used_lineage,
            )

            self.wallpaper_service.set_wallpaper(result.image_path)
            return CycleResult(result.image_path, result.used_seeds, generation)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"C:\Python313\python.exe" -m pytest tests/engine tests/test_history.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add engine database tests
git commit -m "feat: quarantine images below the aesthetic floor, return CycleResult from run()"
```

---

### Task 6: Focus-assist (`is_fullscreen_app_active`)

**Files:**
- Create: `system/focus_assist.py`
- Test: `tests/system/test_focus_assist.py`

**Interfaces:**
- Produces: `is_fullscreen_app_active(user32=None) -> bool`. `user32` defaults to `ctypes.windll.user32`; tests inject a fake. Returns `False` on desktop/shell focus, no foreground window, failed `GetWindowRect`, or any exception (fail open).

- [ ] **Step 1: Write the failing test**

`tests/system/test_focus_assist.py`:

```python
from system.focus_assist import is_fullscreen_app_active

DESKTOP, SHELL = 100, 200


class FakeUser32:
    def __init__(self, hwnd=1, rect=(0, 0, 1920, 1080), screen=(1920, 1080), rect_ok=1, explode=False):
        self.hwnd, self.rect, self.screen, self.rect_ok, self.explode = hwnd, rect, screen, rect_ok, explode

    def GetForegroundWindow(self):
        if self.explode:
            raise OSError("boom")
        return self.hwnd

    def GetDesktopWindow(self):
        return DESKTOP

    def GetShellWindow(self):
        return SHELL

    def GetWindowRect(self, hwnd, rect_ptr):
        left, top, right, bottom = self.rect
        rect_ptr.contents.left, rect_ptr.contents.top = left, top
        rect_ptr.contents.right, rect_ptr.contents.bottom = right, bottom
        return self.rect_ok

    def GetSystemMetrics(self, index):
        return self.screen[index]  # SM_CXSCREEN=0, SM_CYSCREEN=1


def test_fullscreen_window_is_detected():
    assert is_fullscreen_app_active(FakeUser32()) is True


def test_borderless_overscan_window_counts_as_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(rect=(-8, -8, 1928, 1088))) is True


def test_windowed_or_taskbar_clipped_window_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(rect=(100, 100, 900, 700))) is False
    assert is_fullscreen_app_active(FakeUser32(rect=(0, 0, 1920, 1040))) is False


def test_desktop_or_shell_focus_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(hwnd=DESKTOP)) is False
    assert is_fullscreen_app_active(FakeUser32(hwnd=SHELL)) is False


def test_no_foreground_window_is_not_fullscreen():
    assert is_fullscreen_app_active(FakeUser32(hwnd=0)) is False


def test_failed_get_window_rect_fails_open():
    assert is_fullscreen_app_active(FakeUser32(rect_ok=0)) is False


def test_api_exception_fails_open():
    assert is_fullscreen_app_active(FakeUser32(explode=True)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/system/test_focus_assist.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'system.focus_assist'`.

- [ ] **Step 3: Write minimal implementation**

`system/focus_assist.py`:

```python
"""Detect a fullscreen foreground app so generation can defer around games/videos."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

SM_CXSCREEN = 0
SM_CYSCREEN = 1


def is_fullscreen_app_active(user32=None) -> bool:
    """True if the foreground window covers the whole primary screen.

    Fails open: any API problem returns False so generation is never blocked forever.
    """
    try:
        user32 = user32 or ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        # The desktop/shell window spans the screen too; it is not an app to defer for.
        if not hwnd or hwnd in (user32.GetDesktopWindow(), user32.GetShellWindow()):
            return False

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.pointer(rect)):
            return False

        return (
            rect.left <= 0
            and rect.top <= 0
            and rect.right >= user32.GetSystemMetrics(SM_CXSCREEN)
            and rect.bottom >= user32.GetSystemMetrics(SM_CYSCREEN)
        )
    except Exception:
        logging.exception("Fullscreen check failed, treating as not fullscreen")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/system/test_focus_assist.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add system/focus_assist.py tests/system/test_focus_assist.py
git commit -m "feat: add fail-open fullscreen-app detection for focus-assist"
```

---

### Task 7: Global hotkey listener

**Files:**
- Create: `system/hotkeys.py`
- Test: `tests/system/test_hotkeys.py`

**Interfaces:**
- Produces:
  - Constants `MOD_ALT=0x1`, `MOD_CONTROL=0x2`, `VK_LEFT=0x25`, `VK_UP=0x26`, `VK_RIGHT=0x27`, `VK_DOWN=0x28`.
  - `HotkeyListener(bindings: list[tuple[int, int, Callable[[], None]]], user32=None, kernel32=None)` where each binding is `(modifiers, virtual_key, callback)`.
  - `HotkeyListener.run() -> None` — blocking; register, pump messages, dispatch callbacks, unregister on exit. Must run on a dedicated thread (Win32 hotkeys are bound to the registering thread).
  - `HotkeyListener.stop() -> None` — posts `WM_QUIT` to the pump thread; safe to call before `run()` started (no-op).

- [ ] **Step 1: Write the failing test**

`tests/system/test_hotkeys.py`:

```python
from system.hotkeys import (
    MOD_ALT, MOD_CONTROL, VK_LEFT, VK_UP, HotkeyListener,
)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
CTRL_ALT = MOD_CONTROL | MOD_ALT


class FakeUser32:
    def __init__(self, messages=(), fail=()):
        self.messages = list(messages)   # (message, wParam), or -1 to simulate GetMessage error
        self.fail = set(fail)            # (modifiers, vk) combos RegisterHotKey rejects
        self.registered = {}
        self.unregistered = []
        self.posted = []

    def PeekMessageW(self, *args):
        return 0

    def RegisterHotKey(self, hwnd, hotkey_id, modifiers, vk):
        if (modifiers & 0x0F, vk) in self.fail:
            return 0
        self.registered[hotkey_id] = (modifiers & 0x0F, vk)
        return 1

    def GetMessageW(self, ptr, *args):
        if not self.messages:
            return 0
        item = self.messages.pop(0)
        if item == -1:
            return -1
        ptr.contents.message, ptr.contents.wParam = item
        return 1

    def UnregisterHotKey(self, hwnd, hotkey_id):
        self.unregistered.append(hotkey_id)

    def PostThreadMessageW(self, thread_id, message, wparam, lparam):
        self.posted.append((thread_id, message))


class FakeKernel32:
    def GetCurrentThreadId(self):
        return 77


def _listener(user32, calls):
    bindings = [
        (CTRL_ALT, VK_UP, lambda: calls.append("up")),
        (CTRL_ALT, VK_LEFT, lambda: calls.append("left")),
    ]
    return HotkeyListener(bindings, user32=user32, kernel32=FakeKernel32())


def test_dispatches_hotkey_messages_to_matching_callbacks():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 2), (WM_HOTKEY, 1)])

    _listener(user32, calls).run()

    assert calls == ["left", "up"]


def test_ignores_non_hotkey_messages_and_unknown_ids():
    calls = []
    user32 = FakeUser32(messages=[(0x0100, 1), (WM_HOTKEY, 99), (WM_HOTKEY, 1)])

    _listener(user32, calls).run()

    assert calls == ["up"]


def test_failed_registration_skips_that_binding_but_keeps_others():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1), (WM_HOTKEY, 2)], fail=[(CTRL_ALT, VK_UP)])

    _listener(user32, calls).run()

    assert calls == ["left"]


def test_run_returns_immediately_when_nothing_registers():
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1)], fail=[(CTRL_ALT, VK_UP), (CTRL_ALT, VK_LEFT)])

    _listener(user32, []).run()

    assert user32.messages == [(WM_HOTKEY, 1)]  # pump never started


def test_callback_exception_does_not_stop_the_pump():
    calls = []
    user32 = FakeUser32(messages=[(WM_HOTKEY, 1), (WM_HOTKEY, 2)])
    bindings = [
        (CTRL_ALT, VK_UP, lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
        (CTRL_ALT, VK_LEFT, lambda: calls.append("left")),
    ]

    HotkeyListener(bindings, user32=user32, kernel32=FakeKernel32()).run()

    assert calls == ["left"]


def test_get_message_error_ends_the_pump_and_unregisters():
    user32 = FakeUser32(messages=[-1, (WM_HOTKEY, 1)])
    calls = []

    _listener(user32, calls).run()

    assert calls == []
    assert sorted(user32.unregistered) == [1, 2]


def test_stop_posts_quit_to_the_pump_thread_only_after_run_started():
    user32 = FakeUser32()
    listener = _listener(user32, [])

    listener.stop()
    assert user32.posted == []

    listener.run()
    listener.stop()
    assert user32.posted == [(77, WM_QUIT)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/system/test_hotkeys.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'system.hotkeys'`.

- [ ] **Step 3: Write minimal implementation**

`system/hotkeys.py`:

```python
"""Global hotkeys via RegisterHotKey — the only module touching the Win32 hotkey API."""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable
from ctypes import wintypes

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28

WM_QUIT = 0x0012
WM_USER = 0x0400
WM_HOTKEY = 0x0312
PM_NOREMOVE = 0x0000


class HotkeyListener:
    """Registers hotkeys and pumps messages on whichever thread calls run()."""

    def __init__(
        self,
        bindings: list[tuple[int, int, Callable[[], None]]],
        user32=None,
        kernel32=None,
    ) -> None:
        self.bindings = bindings
        self._user32 = user32
        self._kernel32 = kernel32
        self._thread_id: int | None = None

    def run(self) -> None:
        user32 = self._user32 or ctypes.windll.user32
        kernel32 = self._kernel32 or ctypes.windll.kernel32
        msg = wintypes.MSG()

        # Touching the queue first guarantees PostThreadMessage(WM_QUIT) can reach us.
        user32.PeekMessageW(ctypes.pointer(msg), None, WM_USER, WM_USER, PM_NOREMOVE)
        self._thread_id = kernel32.GetCurrentThreadId()

        registered: dict[int, Callable[[], None]] = {}
        for hotkey_id, (modifiers, vk, callback) in enumerate(self.bindings, start=1):
            if user32.RegisterHotKey(None, hotkey_id, modifiers | MOD_NOREPEAT, vk):
                registered[hotkey_id] = callback
            else:
                logging.error(
                    "Hotkey registration failed (modifiers=%#x vk=%#x); likely claimed by another app",
                    modifiers, vk,
                )

        if not registered:
            logging.error("No hotkeys registered; running in auto-generation only mode")
            return

        try:
            while user32.GetMessageW(ctypes.pointer(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam in registered:
                    try:
                        registered[msg.wParam]()
                    except Exception:
                        logging.exception("Hotkey callback failed")
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)

    def stop(self) -> None:
        """Ask the pump to exit. No-op if run() has not started."""
        if self._thread_id is None:
            return
        user32 = self._user32 or ctypes.windll.user32
        user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
```

Note: `test_run_returns_immediately_when_nothing_registers` returns before the `try`, so no unregister is attempted; `test_stop_...` relies on `run()` having set `_thread_id` (true even when the pump ends instantly).

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/system/test_hotkeys.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add system/hotkeys.py tests/system/test_hotkeys.py
git commit -m "feat: add RegisterHotKey-based global hotkey listener"
```

---

### Task 8: `WallpaperDaemon`

**Files:**
- Create: `engine/wallpaper_daemon.py`
- Test: `tests/engine/test_wallpaper_daemon.py`

**Interfaces:**
- Consumes: `WallpaperEngine.run(context=...) -> CycleResult | None` (Task 5); `SeedPool.rate_current(seeds, liked)` (Task 3); `HistoryRepository.load()`; `WallpaperService.set_wallpaper(Path)`; `get_context()` (Task 4); `is_fullscreen_app_active()` (Task 6); `HotkeyListener`, `MOD_*`/`VK_*` (Task 7); settings from Task 1.
- Produces: `WallpaperDaemon(engine, seed_pool, history_repository, wallpaper_service, state_path, is_fullscreen, get_context=get_context, interval=GENERATION_INTERVAL_SECONDS, recheck=FOCUS_ASSIST_RECHECK_SECONDS, listener_factory=HotkeyListener)` with:
  - `.state: dict | None` — `{"seeds": [...], "image_path": str, "generation": int}`, loaded from `state_path` at construction.
  - `.run_cycle() -> None`, `.like()`, `.dislike()`, `.generate_next()`, `.revert()`.
  - `.start()`, `.stop()`, `.run_forever()`.

- [ ] **Step 1: Write the failing test**

`tests/engine/test_wallpaper_daemon.py`:

```python
import json
import threading
import time
from pathlib import Path

from engine.models import CycleResult
from engine.wallpaper_daemon import WallpaperDaemon


class FakeEngine:
    def __init__(self, results=None, fail_first=False):
        self.results = list(results or [])
        self.fail_first = fail_first
        self.contexts = []
        self.runs = 0

    def run(self, context=None):
        self.runs += 1
        self.contexts.append(context)
        if self.fail_first and self.runs == 1:
            raise RuntimeError("bad cycle")
        return self.results.pop(0) if self.results else None


class FakeSeedPool:
    def __init__(self):
        self.rated = []

    def rate_current(self, seeds, liked):
        self.rated.append((seeds, liked))


class FakeHistory:
    def __init__(self, entries=()):
        self.entries = list(entries)

    def load(self):
        return self.entries


class FakeWallpaperService:
    def __init__(self):
        self.set_calls = []

    def set_wallpaper(self, path):
        self.set_calls.append(path)


class FakeListener:
    def __init__(self, bindings):
        self.bindings = bindings
        self.stopped = False

    def run(self):
        pass

    def stop(self):
        self.stopped = True


def _cycle(seeds=(1, 2), generation=3, quarantined=False, path="wallpapers/new.png"):
    return CycleResult(Path(path), list(seeds), generation, quarantined)


def _daemon(tmp_path, engine=None, history=None, fullscreen=lambda: False, interval=0.01, recheck=0.01):
    return WallpaperDaemon(
        engine=engine or FakeEngine(),
        seed_pool=FakeSeedPool(),
        history_repository=history or FakeHistory(),
        wallpaper_service=FakeWallpaperService(),
        state_path=tmp_path / "current_state.json",
        is_fullscreen=fullscreen,
        get_context=lambda: {"time_of_day": "night", "season": "winter"},
        interval=interval,
        recheck=recheck,
        listener_factory=FakeListener,
    )


def wait_until(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# --- state & rating -------------------------------------------------------

def test_successful_cycle_passes_context_and_persists_state(tmp_path):
    engine = FakeEngine([_cycle()])
    daemon = _daemon(tmp_path, engine)

    daemon.run_cycle()

    assert engine.contexts == [{"time_of_day": "night", "season": "winter"}]
    expected = {"seeds": [1, 2], "image_path": str(Path("wallpapers/new.png")), "generation": 3}
    assert daemon.state == expected
    assert json.loads((tmp_path / "current_state.json").read_text()) == expected


def test_state_is_reloaded_by_a_new_daemon(tmp_path):
    _daemon(tmp_path, FakeEngine([_cycle()])).run_cycle()

    reloaded = _daemon(tmp_path)

    assert reloaded.state["seeds"] == [1, 2]


def test_corrupt_state_file_is_ignored(tmp_path):
    (tmp_path / "current_state.json").write_text("{not json")

    assert _daemon(tmp_path).state is None


def test_quarantined_cycle_leaves_state_pointing_at_last_displayed_image(tmp_path):
    engine = FakeEngine([_cycle(seeds=(1, 2)), _cycle(seeds=(8, 9), quarantined=True)])
    daemon = _daemon(tmp_path, engine)

    daemon.run_cycle()
    daemon.run_cycle()
    daemon.like()

    assert daemon.state["seeds"] == [1, 2]
    assert daemon.seed_pool.rated == [([1, 2], True)]


def test_skipped_cycle_leaves_state_untouched(tmp_path):
    daemon = _daemon(tmp_path, FakeEngine([None]))

    daemon.run_cycle()

    assert daemon.state is None


def test_like_and_dislike_rate_current_seeds(tmp_path):
    daemon = _daemon(tmp_path, FakeEngine([_cycle()]))
    daemon.run_cycle()

    daemon.like()
    daemon.dislike()

    assert daemon.seed_pool.rated == [([1, 2], True), ([1, 2], False)]


def test_rating_without_current_state_is_a_noop(tmp_path):
    daemon = _daemon(tmp_path)

    daemon.like()
    daemon.dislike()

    assert daemon.seed_pool.rated == []


# --- revert ---------------------------------------------------------------

def test_revert_sets_second_to_last_non_quarantined_image(tmp_path):
    older, newer = tmp_path / "older.png", tmp_path / "newer.png"
    older.write_bytes(b"x")
    newer.write_bytes(b"x")
    history = FakeHistory([
        {"image_path": str(older)},
        {"image_path": str(newer)},
        {"image_path": "bad.png", "quarantined": True},
    ])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == [older]
    assert daemon.seed_pool.rated == []


def test_revert_with_fewer_than_two_usable_entries_is_a_noop(tmp_path):
    history = FakeHistory([{"image_path": "a.png"}, {"image_path": "b.png", "quarantined": True}])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == []


def test_revert_when_target_image_is_missing_is_a_noop(tmp_path):
    newer = tmp_path / "newer.png"
    newer.write_bytes(b"x")
    history = FakeHistory([{"image_path": str(tmp_path / "gone.png")}, {"image_path": str(newer)}])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == []


# --- scheduler thread -----------------------------------------------------

def test_scheduler_runs_cycles_on_the_interval_and_stops(tmp_path):
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine)

    daemon.start()
    assert wait_until(lambda: engine.runs >= 2)
    daemon.stop()

    assert not daemon._scheduler.is_alive()
    assert daemon._listener.stopped is True


def test_scheduler_survives_a_cycle_that_raises(tmp_path):
    engine = FakeEngine(fail_first=True)
    daemon = _daemon(tmp_path, engine)

    daemon.start()
    assert wait_until(lambda: engine.runs >= 2)
    assert daemon._scheduler.is_alive()
    daemon.stop()


def test_scheduler_defers_while_fullscreen_then_runs(tmp_path):
    engine = FakeEngine()
    state = {"fullscreen": True}
    daemon = _daemon(tmp_path, engine, fullscreen=lambda: state["fullscreen"])

    daemon.start()
    time.sleep(0.15)
    assert engine.runs == 0

    state["fullscreen"] = False
    assert wait_until(lambda: engine.runs >= 1)
    daemon.stop()


def test_generate_next_bypasses_focus_assist_and_the_interval(tmp_path):
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine, fullscreen=lambda: True, interval=60, recheck=60)

    daemon.start()
    time.sleep(0.05)
    assert engine.runs == 0

    daemon.generate_next()
    assert wait_until(lambda: engine.runs == 1)
    daemon.stop()


def test_stop_interrupts_a_long_sleep_promptly(tmp_path):
    daemon = _daemon(tmp_path, interval=60)
    daemon.start()

    started = time.time()
    daemon.stop()

    assert time.time() - started < 2.0
    assert not daemon._scheduler.is_alive()


# --- hotkey wiring --------------------------------------------------------

def test_hotkey_bindings_map_ctrl_alt_arrows_to_daemon_actions(tmp_path):
    from system.hotkeys import MOD_ALT, MOD_CONTROL, VK_DOWN, VK_LEFT, VK_RIGHT, VK_UP

    daemon = _daemon(tmp_path)
    daemon.start()
    bindings = {(mods, vk): cb for mods, vk, cb in daemon._listener.bindings}
    daemon.stop()

    ctrl_alt = MOD_CONTROL | MOD_ALT
    assert bindings[(ctrl_alt, VK_UP)] == daemon.like
    assert bindings[(ctrl_alt, VK_DOWN)] == daemon.dislike
    assert bindings[(ctrl_alt, VK_RIGHT)] == daemon.generate_next
    assert bindings[(ctrl_alt, VK_LEFT)] == daemon.revert
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_daemon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.wallpaper_daemon'`.

- [ ] **Step 3: Write minimal implementation**

`engine/wallpaper_daemon.py`:

```python
"""Resident daemon: scheduled generation on one thread, global hotkeys on another."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from config.settings import FOCUS_ASSIST_RECHECK_SECONDS, GENERATION_INTERVAL_SECONDS
from generation.context_signals import get_context as default_get_context
from system.hotkeys import (
    MOD_ALT, MOD_CONTROL, VK_DOWN, VK_LEFT, VK_RIGHT, VK_UP, HotkeyListener,
)


class WallpaperDaemon:
    """Wraps WallpaperEngine.run() in a timer loop and exposes hotkey actions."""

    def __init__(
        self,
        engine,
        seed_pool,
        history_repository,
        wallpaper_service,
        state_path: Path,
        is_fullscreen,
        get_context=default_get_context,
        interval: float = GENERATION_INTERVAL_SECONDS,
        recheck: float = FOCUS_ASSIST_RECHECK_SECONDS,
        listener_factory=HotkeyListener,
    ) -> None:
        self.engine = engine
        self.seed_pool = seed_pool
        self.history_repository = history_repository
        self.wallpaper_service = wallpaper_service
        self.state_path = state_path
        self.is_fullscreen = is_fullscreen
        self.get_context = get_context
        self.interval = interval
        self.recheck = recheck
        self._listener_factory = listener_factory

        self._wake = threading.Event()   # set by generate_next() or stop()
        self._stop = threading.Event()
        self._scheduler: threading.Thread | None = None
        self._hotkey_thread: threading.Thread | None = None
        self._listener = None
        self.state: dict | None = self._load_state()

    # --- state -----------------------------------------------------------

    def _load_state(self) -> dict | None:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            logging.error("Ignoring unreadable %s: %s", self.state_path, exc)
            return None

    def _save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        tmp_path.replace(self.state_path)
        self.state = state

    # --- one cycle -------------------------------------------------------

    def run_cycle(self) -> None:
        """Run one generation; never raises — a resident process outlives bad cycles."""
        try:
            result = self.engine.run(context=self.get_context())
        except Exception:
            logging.exception("Generation cycle failed, will retry on the next schedule")
            return

        if result is None or result.quarantined:
            return

        self._save_state({
            "seeds": result.used_seeds,
            "image_path": str(result.image_path),
            "generation": result.generation,
        })

    # --- hotkey actions --------------------------------------------------

    def like(self) -> None:
        self._rate(liked=True)

    def dislike(self) -> None:
        self._rate(liked=False)

    def _rate(self, liked: bool) -> None:
        state = self.state
        if not state:
            logging.info("No current wallpaper to rate")
            return
        self.seed_pool.rate_current(state["seeds"], liked=liked)
        logging.info("Rated current wallpaper %s", "up" if liked else "down")

    def generate_next(self) -> None:
        self._wake.set()

    def revert(self) -> None:
        entries = [e for e in self.history_repository.load() if not e.get("quarantined", False)]
        if len(entries) < 2:
            logging.info("No previous wallpaper to revert to")
            return
        previous = Path(entries[-2]["image_path"])
        if not previous.exists():
            logging.warning("Previous wallpaper missing on disk: %s", previous)
            return
        self.wallpaper_service.set_wallpaper(previous)

    def _hotkey_bindings(self) -> list[tuple[int, int, object]]:
        ctrl_alt = MOD_CONTROL | MOD_ALT
        return [
            (ctrl_alt, VK_UP, self.like),
            (ctrl_alt, VK_DOWN, self.dislike),
            (ctrl_alt, VK_RIGHT, self.generate_next),
            (ctrl_alt, VK_LEFT, self.revert),
        ]

    # --- threads ---------------------------------------------------------

    def _scheduler_loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(self.interval)
            while not self._stop.is_set() and not self._wake.is_set() and self.is_fullscreen():
                logging.info("Fullscreen app active, deferring generation")
                self._wake.wait(self.recheck)
            if self._stop.is_set():
                break
            self._wake.clear()
            self.run_cycle()

    def start(self) -> None:
        self._scheduler = threading.Thread(target=self._scheduler_loop, name="scheduler", daemon=True)
        self._listener = self._listener_factory(self._hotkey_bindings())
        self._hotkey_thread = threading.Thread(target=self._listener.run, name="hotkeys", daemon=True)
        self._scheduler.start()
        self._hotkey_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._listener is not None:
            self._listener.stop()
        if self._scheduler is not None:
            self._scheduler.join(timeout=5)

    def run_forever(self) -> None:
        self.start()
        try:
            while self._scheduler.is_alive():
                self._scheduler.join(timeout=0.5)
        except KeyboardInterrupt:
            logging.info("Interrupted, shutting down")
        finally:
            self.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_daemon.py -v`
Expected: PASS (all). Re-run once more to check for thread-timing flakiness.

- [ ] **Step 5: Commit**

```bash
git add engine/wallpaper_daemon.py tests/engine/test_wallpaper_daemon.py
git commit -m "feat: add WallpaperDaemon with scheduler thread, hotkey actions, and persisted state"
```

---

### Task 9: Compose the daemon in `main.py`, document hotkeys, manual verification

**Files:**
- Modify: `main.py`
- Modify: `README.md` (add a short "Daemon" section)

**Interfaces:**
- Consumes: everything above. `build_engine()` is unchanged; `build_daemon()` reuses the engine's own `seed_pool`, `history_repository`, `wallpaper_service` instances so the `SeedPool` lock is shared between the scheduler and hotkey threads.

- [ ] **Step 1: Edit `main.py`**

Add imports:

```python
from config.paths import (
    BEST_SEEDS_FILE, CURRENT_STATE_FILE, HISTORY_FILE, LOG_FILE, WORKFLOW_FILE,
)
from engine.wallpaper_daemon import WallpaperDaemon
from system.focus_assist import is_fullscreen_app_active
```
(replacing the existing `config.paths` import line), then add after `build_engine`:

```python
def build_daemon() -> WallpaperDaemon:
    """Wrap the engine in the resident scheduler + hotkey daemon."""
    engine = build_engine()
    return WallpaperDaemon(
        engine=engine,
        seed_pool=engine.seed_pool,
        history_repository=engine.history_repository,
        wallpaper_service=engine.wallpaper_service,
        state_path=CURRENT_STATE_FILE,
        is_fullscreen=is_fullscreen_app_active,
    )
```

Replace `main()`'s body:

```python
    setup_logging()
    logging.info("Script PID: %s", os.getpid())
    logging.info("Wallpaper daemon started")
    build_daemon().run_forever()
```

- [ ] **Step 2: Add README section**

Append to `README.md`:

```markdown
## Daemon

`python main.py` runs resident: it generates a wallpaper every `GENERATION_INTERVAL_SECONDS`
(deferring while a fullscreen app is focused) and listens for global hotkeys:

| Hotkey | Action |
|---|---|
| `Ctrl+Alt+Up` | Like current wallpaper (boosts its seeds) |
| `Ctrl+Alt+Down` | Dislike current wallpaper (demotes its seeds) |
| `Ctrl+Alt+Right` | Generate the next wallpaper now |
| `Ctrl+Alt+Left` | Revert to the previous wallpaper |

Images scoring below `AESTHETIC_QUALITY_FLOOR` are quarantined (never displayed, seeds zeroed).
```

- [ ] **Step 3: Run the automated suite and import smoke check**

Run: `"C:\Python313\python.exe" -m pytest -q`
Expected: all pass except baseline `tests/test_gene_analytics.py::test_trait_averages`.

Run: `"C:\Python313\python.exe" -c "import main; d = main.build_daemon(); print(d.state, d.seed_pool is d.engine.seed_pool)"`
Expected: prints `None True` (or the saved state) with no traceback.

- [ ] **Step 4: Manual verification (needs the real GPU/ComfyUI/desktop — cannot be automated)**

Run `"C:\Python313\python.exe" main.py` in a terminal and check, in order:
1. Press `Ctrl+Alt+Right` → a cycle starts immediately (log shows it); wallpaper changes; `data/current_state.json` appears with `seeds`/`image_path`/`generation`.
2. Press `Ctrl+Alt+Up`; in `data/best_seeds.json` the two current seeds' `score` rose 1.5×. Press `Ctrl+Alt+Down`; they drop 0.3×.
3. Press `Ctrl+Alt+Right` twice more; after a reuse-branch cycle, `best_seeds.json` has records with `parent_seed` set and `generation` ≥ 1.
4. Press `Ctrl+Alt+Left` → wallpaper switches back to the previous image; `best_seeds.json` unchanged.
5. Quarantine: temporarily set `AESTHETIC_QUALITY_FLOOR = 10.0`, restart, press `Ctrl+Alt+Right` → wallpaper does NOT change, `history.json` last entry has `"quarantined": true`, `current_state.json` unchanged. Restore `4.0`.
6. Focus-assist: temporarily set `GENERATION_INTERVAL_SECONDS = 20` and `FOCUS_ASSIST_RECHECK_SECONDS = 10`, restart, put a video/browser in F11 fullscreen → log shows "Fullscreen app active, deferring generation" and no cycle runs; exit fullscreen → cycle runs. Click the empty desktop → cycle still runs. Restore both constants.
7. `Ctrl+C` → daemon exits cleanly; hotkeys are released (pressing them no longer logs anything).
8. If any hotkey logs "registration failed", another app owns that combo — confirm the daemon still generates on schedule.

- [ ] **Step 5: Commit**

```bash
git add main.py README.md
git commit -m "feat: run the wallpaper engine as a resident daemon with hotkeys"
```

---

## Self-Review

**Spec coverage:** settings constants → T1; mutation + lineage + `WorkflowManager`/`ComfyBackend`/`GenerationResult` ripple → T2; `rate_current`/`penalize` → T3; `context_signals` + `PromptEngine` context → T4; quality floor/quarantine/`quarantined` history field/engine return info → T5; `focus_assist` → T6; `hotkeys` → T7; daemon (threads, `current_state.json`, generate-next bypass, revert, survives bad cycle, no-state no-op) → T8; `main.py` composition → T9. Error-handling bullets: no-state hotkey (T8), `RegisterHotKey` failure (T7), revert with no prior entry (T8), quarantine leaves state (T5+T8), bad cycle (T8).

**Deviations from the spec, deliberate:**
- `record_result` takes `lineage` as a trailing optional kwarg (spec shows it positional second) to honor the spec's own "existing signature stays" constraint.
- Win32 modules take an injectable `user32`, so focus-assist and the hotkey pump are unit-tested with fakes; spec called them manual-only. Real-hardware behavior is still covered by Task 9 step 4.
- Added: seed clamping to `[0, 2**63-1]`, desktop/shell exclusion in focus-assist, a repository lock in `SeedPool`, missing-file guard in revert — all from the Review Focus list.
- Scheduler waits one interval before its first cycle (spec data flow); `Ctrl+Alt+Right` is the way to generate right after launch.

**Placeholder scan:** none — every step has literal code/commands.

**Type consistency:** `next_seed() -> (seed, parent_seed, generation)` (T2) is what `WorkflowManager.prepare` unpacks (T2) and what `FakeSeedPool` in the workflow tests returns; `used_lineage: list[tuple[int | None, int]]` is identical in `GenerationResult`, `prepare`, `record_result(lineage=)`, and the engine's `max(g for _, g in ...)`; `CycleResult(image_path, used_seeds, generation, quarantined)` (T5) matches daemon usage and the `_cycle()` test helper (T8); `HotkeyListener(bindings)` tuple shape `(modifiers, vk, callback)` matches `_hotkey_bindings()`; `engine.run(context=...)` matches `FakeEngine.run(self, context=None)`.
