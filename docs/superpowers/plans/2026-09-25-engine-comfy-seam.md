# Engine ↔ ComfyUI Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carve a boundary between wallpaper-engine domain logic and the ComfyUI generation backend so ComfyUI-specific concepts (workflow JSON, node IDs, HTTP polling, process lifecycle) never leak outside `generation/comfy/`, while preserving today's exact generation behavior.

**Architecture:** New `engine/` package owns the one-cycle orchestration (`WallpaperEngine`) and plain dataclasses (`GenerationRequest`, `GenerationResult`, `EvaluationResult`). `generation/comfy/backend.py::ComfyBackend` is the sole file that translates between those dataclasses and ComfyUI's workflow JSON/HTTP API. No `Protocol`/ABC layer — one backend, one strategy, duck typing is enough. `evaluation/`, `database/`, `system/`, `config/` get responsibility-based reorganization with minimal renames.

**Tech Stack:** Python 3.13, pytest, requests, torch/clip (unchanged deps).

**Spec:** `docs/superpowers/specs/2026-09-25-engine-comfy-seam-design.md`

## Global Constraints

- Local Windows side project — no Protocol/ABC interfaces for single-implementation boundaries (spec priority 6).
- Preserve current behavior exactly: same constants, same node IDs (`6`, `8`, `17`, `20`, `23`), same seed-reuse probability, same 0.4/0.6 semantic/aesthetic score weighting (spec priority 3).
- No renames without justification; `database/` keeps its name (spec priority 7).
- Out of scope: candidates, new scoring dimensions, scheduling/daemon, UI, personalization (spec priority 8).
- Test runner for this repo: `"C:\Python313\python.exe" -m pytest <path> -v` (confirmed working; the WindowsApps `python3` alias has no pytest installed).
- Baseline before this plan: `tests/test_gene_analytics.py::test_trait_averages` fails on main already (pre-existing bug in `GeneAnalytics`, unrelated to this refactor — out of scope, do not fix). `tests/test_prompt_engine.py` fails on main (tests the dead v1 `PromptEngine` with a broken call signature — this file is deleted in Task 1, not fixed).
- `core/aesthetic_scorer.py` loads a weights file via `Path(__file__).resolve().parent / "sa_0_4_vit_l_14_linear.pth"` — this file must move with it.
- No `__init__.py` files exist in `comfy/`, `config/`, `core/`, `database/`, `system/` (implicit namespace packages) — new packages (`engine/`, `generation/`, `generation/comfy/`, `evaluation/`) follow the same convention, no `__init__.py` added.

## Review Focus

- **Seed count mismatch**: if a future workflow JSON has a different number of `KSampler` nodes than seeds available, `WorkflowManager.prepare` must still raise (today's `RuntimeError("No KSampler node found")` behavior) rather than silently under/over-consuming — Task 4's test pins the two-KSampler case explicitly.
- **ComfyUI returning a history entry with `status_str == "error"`**: `ComfyBackend.generate` must propagate today's `None`-return-on-failure behavior, not raise unexpectedly — Task 5's test covers it.
- **GPU never idles**: `WallpaperEngine.run()` must still exit quietly after `GPU_IDLE_RETRIES` attempts, not raise or hang — Task 8's test covers it.
- **ComfyUI server never boots**: `WallpaperEngine.run()` must log and return without crashing, matching today's `main.py` behavior — Task 8's test covers it.
- **Lazy evaluator construction actually deferring the CLIP import**: a run that exits early (GPU busy, boot failure, generation failure) must never trigger `import evaluation.semantic_scorer` — Task 8's test asserts the evaluator factory is never invoked on those paths.

---

### Task 1: Delete dead v1 code, split config into `settings.py` + `prompt_grammar.py`

**Files:**
- Delete: `core/prompt_engine.py`, `tests/test_prompt_engine.py`, `test_prompt_engine.py` (repo root, untracked)
- Delete: `config/constants.py`, `config/constants_v2.py`
- Create: `config/settings.py`
- Create: `config/prompt_grammar.py`
- Modify: `comfy/workflow.py`, `comfy/client.py`, `comfy/server.py`, `system/gpu.py`, `core/prompt_engine_v2.py` (import statements only)
- Test: `tests/config/test_settings.py`

**Interfaces:**
- Produces: `config.settings.{COMFY_URL, WORKFLOW_PROMPT_NODE_ID, WORKFLOW_KSAMPLER_FIRST_NODE_ID, WORKFLOW_KSAMPLER_SECOND_NODE_ID, WORKFLOW_IMAGE_SHARPEN_NODE_ID, WORKFLOW_LATENT_UPSCALE_NODE_ID, GPU_INDEX, GPU_IDLE_THRESHOLD, GPU_IDLE_RETRIES, GPU_IDLE_WAIT_SECONDS, COMFY_BOOT_RETRIES, COMFY_BOOT_WAIT_SECONDS, GENERATION_TIMEOUT_SECONDS, HISTORY_POLL_SECONDS, BEST_SEED_MUTATION_RANGE, BEST_SEED_REUSE_PROBABILITY, BEST_SEED_LIMIT}` — used by Tasks 2, 4, 5, 8.
- Produces: `config.prompt_grammar` — everything currently in `config/constants_v2.py` except its infra tail (same names: `THEMES`, `MOOD_SEMANTICS`, `LIGHTING_TIME`, `FRAMING_TYPE`, `LENS_CHARACTER`, `RENDER_MEDIUM`, `RENDER_QUALITY_MARKERS`, `RENDER_TEMPLATES`, `SCENE_SUFFIX`, `SEMANTIC_TEMPLATES_BY_TYPE`, `CAMERA_ANGLE`, `MAX_SCENE_DENSITY`, `TraitPairMemory`, `DiversityTracker`, `is_lighting_compatible`, `is_lens_framing_compatible`, `is_camera_angle_framing_compatible`, `get_environmental_condition`, `get_mood_list`, `apply_mood_theme_weight`, `apply_mood_condition_weight`, `apply_render_stability`, `get_camera_angle_affinity_boost`, `score_scene_density`) — used by Task 7.

`config/constants.py`'s infra tail (lines 216-232 of the current file) and `config/constants_v2.py`'s infra tail (lines 1668-1682) are byte-for-byte identical value sets — use `constants_v2.py`'s copy (has `BEST_SEED_REUSE_PROBABILITY = 0.45`, the more recent value; `constants.py`'s `0.7` is stale — confirmed by reading both files, `constants_v2.py` is the actively-imported one via `core/prompt_engine_v2.py`, `constants.py`'s copy is dead alongside v1).

- [ ] **Step 1: Write the failing test**

```python
# tests/config/test_settings.py
from config import settings


def test_infra_constants_present_and_correct():
    assert settings.COMFY_URL == "http://127.0.0.1:8188"
    assert settings.WORKFLOW_PROMPT_NODE_ID == "6"
    assert settings.WORKFLOW_KSAMPLER_FIRST_NODE_ID == "8"
    assert settings.WORKFLOW_KSAMPLER_SECOND_NODE_ID == "17"
    assert settings.WORKFLOW_LATENT_UPSCALE_NODE_ID == "20"
    assert settings.WORKFLOW_IMAGE_SHARPEN_NODE_ID == "23"
    assert settings.GPU_INDEX == "0"
    assert settings.GPU_IDLE_THRESHOLD == 50
    assert settings.GPU_IDLE_RETRIES == 5
    assert settings.GPU_IDLE_WAIT_SECONDS == 120
    assert settings.COMFY_BOOT_RETRIES == 30
    assert settings.COMFY_BOOT_WAIT_SECONDS == 2
    assert settings.GENERATION_TIMEOUT_SECONDS == 300
    assert settings.HISTORY_POLL_SECONDS == 2
    assert settings.BEST_SEED_MUTATION_RANGE == 5000
    assert settings.BEST_SEED_REUSE_PROBABILITY == 0.45
    assert settings.BEST_SEED_LIMIT == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config.settings'`

- [ ] **Step 3: Create `config/settings.py`**

```python
"""Infra constants: ComfyUI endpoint, workflow node IDs, timing, seed pool params."""

COMFY_URL                       = "http://127.0.0.1:8188"
WORKFLOW_PROMPT_NODE_ID         = "6"
WORKFLOW_KSAMPLER_FIRST_NODE_ID  = "8"
WORKFLOW_KSAMPLER_SECOND_NODE_ID = "17"
WORKFLOW_LATENT_UPSCALE_NODE_ID  = "20"
WORKFLOW_IMAGE_SHARPEN_NODE_ID    = "23"
GPU_INDEX                       = "0"
GPU_IDLE_THRESHOLD              = 50
GPU_IDLE_RETRIES                = 5
GPU_IDLE_WAIT_SECONDS            = 120
COMFY_BOOT_RETRIES               = 30
COMFY_BOOT_WAIT_SECONDS          = 2
GENERATION_TIMEOUT_SECONDS        = 300
HISTORY_POLL_SECONDS             = 2
BEST_SEED_MUTATION_RANGE          = 5000
BEST_SEED_REUSE_PROBABILITY       = 0.45
BEST_SEED_LIMIT                  = 50
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/config/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Create `config/prompt_grammar.py`**

Copy the entire contents of `config/constants_v2.py` (lines 1-1663, i.e. everything up to but not including the `# COMFYUI / GENERATION CONSTANTS` section at the bottom) into `config/prompt_grammar.py` verbatim — no logic changes, same names, same `TraitPairMemory`/`DiversityTracker` classes, same compatibility tables and helper functions. Drop only the infra-constant tail (`COMFY_URL` through `BEST_SEED_LIMIT`, lines 1668-1682).

- [ ] **Step 6: Update `core/prompt_engine_v2.py`'s import**

Change:
```python
from config.constants_v2 import (
```
to:
```python
from config.prompt_grammar import (
```
(same imported names, no other changes to this file in this task — it still lives at `core/prompt_engine_v2.py` until Task 7).

- [ ] **Step 7: Update remaining importers to use `config.settings`**

In `comfy/workflow.py`, change:
```python
from config.constants import (
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_IMAGE_SHARPEN_NODE_ID,
    WORKFLOW_LATENT_UPSCALE_NODE_ID,
    WORKFLOW_KSAMPLER_FIRST_NODE_ID,
    WORKFLOW_KSAMPLER_SECOND_NODE_ID
)
```
to:
```python
from config.settings import (
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_IMAGE_SHARPEN_NODE_ID,
    WORKFLOW_LATENT_UPSCALE_NODE_ID,
    WORKFLOW_KSAMPLER_FIRST_NODE_ID,
    WORKFLOW_KSAMPLER_SECOND_NODE_ID
)
```

In `comfy/client.py`, change:
```python
from config.constants import COMFY_URL, GENERATION_TIMEOUT_SECONDS, HISTORY_POLL_SECONDS
```
to:
```python
from config.settings import COMFY_URL, GENERATION_TIMEOUT_SECONDS, HISTORY_POLL_SECONDS
```

In `comfy/server.py`, change:
```python
from config.constants import COMFY_URL
```
to:
```python
from config.settings import COMFY_URL
```

In `system/gpu.py`, change:
```python
from config.constants import GPU_IDLE_THRESHOLD, GPU_INDEX
```
to:
```python
from config.settings import GPU_IDLE_THRESHOLD, GPU_INDEX
```

- [ ] **Step 8: Delete dead files**

```bash
git rm core/prompt_engine.py tests/test_prompt_engine.py config/constants.py config/constants_v2.py
rm -f test_prompt_engine.py
```

- [ ] **Step 9: Update `main.py`'s dead v1 branch**

In `main.py`, remove the `v2PromptEnabled` flag, the `PromptEngine` import, and the `if/else` branch in `WallpaperApplication.__init__`:

Change:
```python
from core.prompt_engine import PromptEngine
from core.prompt_engine_v2 import PromptEngineV2
```
to:
```python
from core.prompt_engine_v2 import PromptEngineV2
```

Change:
```python
v2PromptEnabled = True

def setup_logging() -> None:
```
to:
```python
def setup_logging() -> None:
```

Change:
```python
        if v2PromptEnabled: 
            self.prompt_engine = PromptEngineV2()
        else: 
            self.prompt_engine = PromptEngine()
```
to:
```python
        self.prompt_engine = PromptEngineV2()
```

(`main.py` gets fully rewritten in Task 8; this step only keeps it important between now and then.)

- [ ] **Step 10: Run full suite to confirm nothing else broke**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: `tests/config/test_settings.py::test_infra_constants_present_and_correct PASS`, `tests/test_history.py::test_history_entry_saved PASS`, `tests/test_seed_engine.py::test_seed_is_integer PASS`, `tests/test_gene_analytics.py::test_trait_averages FAIL` (pre-existing, out of scope). `tests/test_prompt_engine.py` no longer collected (deleted).

- [ ] **Step 11: Commit**

```bash
git add config/settings.py config/prompt_grammar.py comfy/workflow.py comfy/client.py comfy/server.py system/gpu.py core/prompt_engine_v2.py main.py tests/config/test_settings.py
git commit -m "Delete dead v1 prompt engine, split config into settings + prompt_grammar"
```

---

### Task 2: `engine/models.py` — GenerationRequest, GenerationResult, EvaluationResult

**Files:**
- Create: `engine/models.py`
- Test: `tests/engine/test_models.py`

**Interfaces:**
- Produces: `engine.models.GenerationRequest(prompt: str, dna: dict[str, object])`, `engine.models.GenerationResult(image_path: Path, used_seeds: list[int], generation_time_seconds: float)`, `engine.models.EvaluationResult(semantic_score: float, aesthetic_score: float, combined_score: float)` — used by Tasks 5, 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_models.py
from pathlib import Path

from engine.models import GenerationRequest, GenerationResult, EvaluationResult


def test_generation_request_holds_prompt_and_dna():
    req = GenerationRequest(prompt="a cat", dna={"theme": "fantasy"})
    assert req.prompt == "a cat"
    assert req.dna == {"theme": "fantasy"}


def test_generation_result_holds_output_shape():
    result = GenerationResult(
        image_path=Path("wallpapers/foo.png"),
        used_seeds=[1, 2],
        generation_time_seconds=12.5,
    )
    assert result.image_path == Path("wallpapers/foo.png")
    assert result.used_seeds == [1, 2]
    assert result.generation_time_seconds == 12.5


def test_evaluation_result_holds_scores():
    result = EvaluationResult(semantic_score=80.0, aesthetic_score=6.5, combined_score=5.9)
    assert result.semantic_score == 80.0
    assert result.aesthetic_score == 6.5
    assert result.combined_score == 5.9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine'`

- [ ] **Step 3: Write the implementation**

```python
# engine/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_models.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add engine/models.py tests/engine/test_models.py
git commit -m "Add engine domain dataclasses: GenerationRequest, GenerationResult, EvaluationResult"
```

---

### Task 3: `engine/seed_pool.py` — SeedPool (renamed from SeedEngine)

**Files:**
- Create: `engine/seed_pool.py`
- Delete: `core/seed_engine.py`, `tests/test_seed_engine.py`
- Test: `tests/engine/test_seed_pool.py`

**Interfaces:**
- Consumes: `database.seeds.SeedRepository` (unchanged — `load()`, `save(records)`), `config.settings.{BEST_SEED_LIMIT, BEST_SEED_REUSE_PROBABILITY}` (from Task 1).
- Produces: `engine.seed_pool.SeedPool(repository: SeedRepository)` with `.next_seed() -> int` and `.record_result(seeds: list[int], score: float, prompt: str, theme: str) -> None` — used by Tasks 4, 5, 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_seed_pool.py
from engine.seed_pool import SeedPool
from database.seeds import SeedRepository


def test_next_seed_is_integer(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    seed = pool.next_seed()

    assert isinstance(seed, int)


def test_record_result_persists_ranked_by_score(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111, 222], score=0.9, prompt="a cat", theme="fantasy")
    pool.record_result(seeds=[333], score=0.1, prompt="a dog", theme="space")

    records = repo.load()
    assert len(records) == 3
    assert records[0]["score"] == 0.9
    assert records[-1]["score"] == 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_seed_pool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.seed_pool'`

- [ ] **Step 3: Write the implementation**

```python
# engine/seed_pool.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_seed_pool.py -v`
Expected: PASS (2/2)

- [ ] **Step 5: Delete old files**

```bash
git rm core/seed_engine.py tests/test_seed_engine.py
```

- [ ] **Step 6: Run full suite**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: `tests/engine/test_seed_pool.py` 2/2 PASS, `tests/test_history.py` PASS, `tests/test_gene_analytics.py` FAIL (pre-existing). `tests/test_seed_engine.py` no longer collected.

- [ ] **Step 7: Commit**

```bash
git add engine/seed_pool.py tests/engine/test_seed_pool.py
git commit -m "Move SeedEngine to engine/seed_pool.py, rename to SeedPool"
```

---

### Task 4: Move `comfy/` → `generation/comfy/`, invert `WorkflowManager`'s seed dependency

**Files:**
- Create: `generation/comfy/client.py`, `generation/comfy/server.py`, `generation/comfy/workflow.py`
- Delete: `comfy/client.py`, `comfy/server.py`, `comfy/workflow.py` (the now-empty `comfy/` directory)
- Test: `tests/generation/comfy/test_workflow.py`

**Interfaces:**
- Consumes: any object with `.next_seed() -> int` (duck-typed — `engine.seed_pool.SeedPool` satisfies this from Task 3, but `WorkflowManager` does not import `engine.seed_pool`).
- Produces: `generation.comfy.workflow.WorkflowManager(workflow_path: Path, seeds).prepare(final_prompt: str, dna: dict) -> tuple[dict, list[int]]` — used by Task 5. `generation.comfy.client.ComfyClient`, `generation.comfy.server.ComfyServer` unchanged, used by Task 5.

- [ ] **Step 1: Move the files, preserving history**

```bash
git mv comfy/client.py generation/comfy/client.py
git mv comfy/server.py generation/comfy/server.py
git mv comfy/workflow.py generation/comfy/workflow.py
```

(`client.py` and `server.py` need no content changes — their `config.settings` imports were already fixed in Task 1 and travel with the move.)

- [ ] **Step 2: Write the failing test for the inverted seed dependency**

```python
# tests/generation/comfy/test_workflow.py
import json

from generation.comfy.workflow import WorkflowManager


class FakeSeedPool:
    def __init__(self, seeds):
        self._seeds = iter(seeds)
        self.calls = 0

    def next_seed(self):
        self.calls += 1
        return next(self._seeds)


def _write_fake_workflow(path):
    workflow = {
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "8": {"class_type": "KSampler", "inputs": {"seed": 0, "cfg": 0, "steps": 0, "sampler_name": ""}},
        "17": {"class_type": "KSampler", "inputs": {"seed": 0, "cfg": 0, "steps": 0, "denoise": 0, "sampler_name": ""}},
        "20": {"class_type": "LatentUpscaleBy", "inputs": {"scale_by": 0}},
        "23": {"class_type": "ImageSharpen", "inputs": {"alpha": 0}},
    }
    path.write_text(json.dumps(workflow), encoding="utf-8")


def test_prepare_pulls_one_seed_per_ksampler_and_injects_prompt(tmp_path):
    workflow_path = tmp_path / "wallpaper.json"
    _write_fake_workflow(workflow_path)
    seeds = FakeSeedPool([111, 222])

    manager = WorkflowManager(workflow_path, seeds)
    workflow, used_seeds = manager.prepare(
        final_prompt="a cinematic castle",
        dna={"theme": "fantasy", "scene_density_score": 5, "subject_type": "structure", "mood": "mythic and ancient"},
    )

    assert seeds.calls == 2
    assert used_seeds == [111, 222]
    assert workflow["6"]["inputs"]["text"] == "a cinematic castle"
    assert workflow["8"]["inputs"]["seed"] == 111
    assert workflow["17"]["inputs"]["seed"] == 222


def test_prepare_raises_when_no_ksampler_present(tmp_path):
    workflow_path = tmp_path / "wallpaper.json"
    workflow_path.write_text(json.dumps({"6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}}), encoding="utf-8")
    seeds = FakeSeedPool([111])

    manager = WorkflowManager(workflow_path, seeds)

    import pytest
    with pytest.raises(RuntimeError, match="No KSampler node found"):
        manager.prepare(final_prompt="x", dna={"theme": "fantasy"})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/comfy/test_workflow.py -v`
Expected: FAIL — `WorkflowManager.__init__` still requires a `SeedEngine`-shaped `seed_engine` argument and calls `.get_seed()`, which `FakeSeedPool` doesn't have.

- [ ] **Step 4: Update `WorkflowManager` to accept a duck-typed seed source**

In `generation/comfy/workflow.py`, change:
```python
from core.seed_engine import SeedEngine
from config.constants import (
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_IMAGE_SHARPEN_NODE_ID,
    WORKFLOW_LATENT_UPSCALE_NODE_ID,
    WORKFLOW_KSAMPLER_FIRST_NODE_ID,
    WORKFLOW_KSAMPLER_SECOND_NODE_ID
)


class WorkflowManager:
    """Loads and updates the ComfyUI workflow payload."""

    def __init__(self, workflow_path: Path, seed_engine: SeedEngine) -> None:
        self.workflow_path = workflow_path
        self.seed_engine = seed_engine
```
to:
```python
from config.settings import (
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_IMAGE_SHARPEN_NODE_ID,
    WORKFLOW_LATENT_UPSCALE_NODE_ID,
    WORKFLOW_KSAMPLER_FIRST_NODE_ID,
    WORKFLOW_KSAMPLER_SECOND_NODE_ID
)


class WorkflowManager:
    """Loads and updates the ComfyUI workflow payload.

    `seeds` is any object exposing `.next_seed() -> int` — duck-typed so this
    module never needs to know about the engine's seed pool implementation.
    """

    def __init__(self, workflow_path: Path, seeds) -> None:
        self.workflow_path = workflow_path
        self.seeds = seeds
```

And change the one call site inside `prepare()`:
```python
                seed = self.seed_engine.get_seed()
```
to:
```python
                seed = self.seeds.next_seed()
```

(No other logic in `workflow.py` changes — `_build_profile`, `_clamp`, node-walking loop, and error raises stay exactly as they are today.)

- [ ] **Step 5: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/comfy/test_workflow.py -v`
Expected: PASS (2/2)

- [ ] **Step 6: Run full suite**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: previous results unchanged, plus `tests/generation/comfy/test_workflow.py` 2/2 PASS. `comfy/` directory now empty — leave its removal to git (an empty dir isn't tracked once its files are gone).

- [ ] **Step 7: Commit**

```bash
git add generation/comfy/client.py generation/comfy/server.py generation/comfy/workflow.py tests/generation/comfy/test_workflow.py
git commit -m "Move comfy/ to generation/comfy/, invert WorkflowManager's seed dependency to duck typing"
```

---

### Task 5: `generation/comfy/backend.py` — ComfyBackend

**Files:**
- Create: `generation/comfy/backend.py`
- Test: `tests/generation/comfy/test_backend.py`

**Interfaces:**
- Consumes: `generation.comfy.client.ComfyClient`, `generation.comfy.server.ComfyServer`, `generation.comfy.workflow.WorkflowManager` (Task 4), `system.file_manager.FileManager` (unchanged, existing `move_generated_image(filename: str, subfolder: str) -> Path`), `engine.models.GenerationRequest`/`GenerationResult` (Task 2), `config.settings.{COMFY_BOOT_RETRIES, COMFY_BOOT_WAIT_SECONDS}` (Task 1).
- Produces: `generation.comfy.backend.ComfyBackend(client, server, workflow, file_manager)` with `.ensure_ready() -> bool` and `.generate(request: GenerationRequest, seeds) -> GenerationResult | None` — used by Task 8.

Design note: `ComfyBackend` is given the `FileManager` and calls `move_generated_image` itself, so `GenerationResult.image_path` is always the final wallpapers-directory path — `filename`/`subfolder` (ComfyUI history-API concepts) never cross out of `generation/comfy/`. This keeps `FileManager`'s existing signature untouched per the spec's module-responsibility table while finishing the seam.

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/comfy/test_backend.py
import time
from pathlib import Path

from engine.models import GenerationRequest
from generation.comfy.backend import ComfyBackend


class FakeSeedPool:
    def next_seed(self):
        return 42


class FakeWorkflowManager:
    def prepare(self, final_prompt, dna):
        return {"workflow": "payload"}, [42, 43]


class FakeFileManager:
    def move_generated_image(self, filename, subfolder):
        return Path("wallpapers") / filename


def test_generate_returns_generation_result_on_success():
    class FakeClient:
        def queue_prompt(self, workflow):
            return "prompt-id-1"

        def wait_for_image(self, prompt_id):
            assert prompt_id == "prompt-id-1"
            return {"filename": "out.png", "subfolder": "sub"}

    backend = ComfyBackend(
        client=FakeClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
        FakeSeedPool(),
    )

    assert result is not None
    assert result.image_path == Path("wallpapers/out.png")
    assert result.used_seeds == [42, 43]
    assert result.generation_time_seconds >= 0


def test_generate_returns_none_when_queue_fails():
    class FailingClient:
        def queue_prompt(self, workflow):
            return None

        def wait_for_image(self, prompt_id):
            raise AssertionError("should not be called")

    backend = ComfyBackend(
        client=FailingClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
        FakeSeedPool(),
    )

    assert result is None


def test_generate_returns_none_when_image_wait_fails():
    class TimeoutClient:
        def queue_prompt(self, workflow):
            return "prompt-id-1"

        def wait_for_image(self, prompt_id):
            return None

    backend = ComfyBackend(
        client=TimeoutClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
        FakeSeedPool(),
    )

    assert result is None


def test_ensure_ready_returns_true_when_already_running():
    class RunningServer:
        def is_running(self):
            return True

        def start(self):
            raise AssertionError("should not start when already running")

    backend = ComfyBackend(
        client=None, server=RunningServer(), workflow=None, file_manager=None,
    )

    assert backend.ensure_ready() is True


def test_ensure_ready_starts_server_and_waits_for_boot():
    class BootingServer:
        def __init__(self):
            self.checks = 0
            self.started = False

        def is_running(self):
            self.checks += 1
            if not self.started:
                return False
            return self.checks > 2

        def start(self):
            self.started = True

    backend = ComfyBackend(
        client=None, server=BootingServer(), workflow=None, file_manager=None,
    )

    assert backend.ensure_ready() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/comfy/test_backend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation.comfy.backend'`

- [ ] **Step 3: Write the implementation**

```python
# generation/comfy/backend.py
"""ComfyUI generation backend — the only file that translates domain
GenerationRequest/GenerationResult to and from ComfyUI's workflow JSON
and HTTP API."""

from __future__ import annotations

import logging
import time

from config.settings import COMFY_BOOT_RETRIES, COMFY_BOOT_WAIT_SECONDS
from engine.models import GenerationRequest, GenerationResult


class ComfyBackend:
    """Generation backend adapter for a local ComfyUI instance."""

    def __init__(self, client, server, workflow, file_manager) -> None:
        self.client = client
        self.server = server
        self.workflow = workflow
        self.file_manager = file_manager

    def ensure_ready(self) -> bool:
        """Start the ComfyUI process if it isn't running, and wait for it to boot."""
        if self.server.is_running():
            return True

        logging.info("ComfyUI not running. Starting...")
        self.server.start()

        for _ in range(COMFY_BOOT_RETRIES):
            if self.server.is_running():
                logging.info("ComfyUI started successfully")
                return True
            time.sleep(COMFY_BOOT_WAIT_SECONDS)
        return False

    def generate(self, request: GenerationRequest, seeds) -> GenerationResult | None:
        """Submit a generation request to ComfyUI and return the result, or None on failure."""
        start_time = time.time()

        workflow, used_seeds = self.workflow.prepare(request.prompt, request.dna)

        prompt_id = self.client.queue_prompt(workflow)
        if not prompt_id:
            return None

        image_info = self.client.wait_for_image(prompt_id)
        if not image_info:
            return None

        destination = self.file_manager.move_generated_image(
            filename=image_info["filename"],
            subfolder=image_info["subfolder"],
        )

        return GenerationResult(
            image_path=destination,
            used_seeds=used_seeds,
            generation_time_seconds=round(time.time() - start_time, 2),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/comfy/test_backend.py -v`
Expected: PASS (5/5)

- [ ] **Step 5: Commit**

```bash
git add generation/comfy/backend.py tests/generation/comfy/test_backend.py
git commit -m "Add ComfyBackend: the only file that touches ComfyUI workflow JSON and HTTP API"
```

---

### Task 6: Move `evaluation/` (CLIP backbone, aesthetic scorer, semantic scorer)

**Files:**
- Create: `evaluation/clip_backbone.py`, `evaluation/aesthetic_scorer.py`, `evaluation/semantic_scorer.py`, `evaluation/sa_0_4_vit_l_14_linear.pth`
- Delete: `core/clip_manager.py`, `core/aesthetic_scorer.py`, `core/semantic_scorer.py`, `core/sa_0_4_vit_l_14_linear.pth`
- Test: `tests/evaluation/test_module_shape.py`

**Interfaces:**
- Produces: `evaluation.semantic_scorer.SemanticPromptScorer`, `evaluation.aesthetic_scorer.AestheticScorer` — imported lazily by Task 8's `WallpaperEngine`.

No behavior change — this is a pure relocation. Actually instantiating these classes loads CLIP (a multi-second GPU/CPU model load), so the test only checks the classes are importable and have the expected methods, without constructing them.

- [ ] **Step 1: Write the failing test**

```python
# tests/evaluation/test_module_shape.py
def test_semantic_scorer_importable_with_score_method():
    from evaluation.semantic_scorer import SemanticPromptScorer
    assert hasattr(SemanticPromptScorer, "score")


def test_aesthetic_scorer_importable_with_score_method():
    from evaluation.aesthetic_scorer import AestheticScorer
    assert hasattr(AestheticScorer, "score")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/evaluation/test_module_shape.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evaluation'`

- [ ] **Step 3: Move the files, preserving history**

```bash
git mv core/clip_manager.py evaluation/clip_backbone.py
git mv core/aesthetic_scorer.py evaluation/aesthetic_scorer.py
git mv core/semantic_scorer.py evaluation/semantic_scorer.py
git mv core/sa_0_4_vit_l_14_linear.pth evaluation/sa_0_4_vit_l_14_linear.pth
```

- [ ] **Step 4: Update their imports**

In `evaluation/aesthetic_scorer.py`, change:
```python
from core.clip_manager import (
    device,
    model,
    preprocess,
)
```
to:
```python
from evaluation.clip_backbone import (
    device,
    model,
    preprocess,
)
```

In `evaluation/semantic_scorer.py`, apply the identical change.

(`evaluation/aesthetic_scorer.py`'s weights-path line, `Path(__file__).resolve().parent / "sa_0_4_vit_l_14_linear.pth"`, needs no edit — it's already relative to the file's own directory, which now correctly resolves to `evaluation/`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/evaluation/test_module_shape.py -v`
Expected: PASS (2/2)

- [ ] **Step 6: Run full suite**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: previous results unchanged, plus `tests/evaluation/test_module_shape.py` 2/2 PASS.

- [ ] **Step 7: Commit**

```bash
git add evaluation/clip_backbone.py evaluation/aesthetic_scorer.py evaluation/semantic_scorer.py evaluation/sa_0_4_vit_l_14_linear.pth tests/evaluation/test_module_shape.py
git commit -m "Move CLIP backbone and scorers from core/ to evaluation/"
```

---

### Task 7: `generation/prompt_engine.py` — rename PromptEngineV2 to PromptEngine

**Files:**
- Create: `generation/prompt_engine.py`
- Delete: `core/prompt_engine_v2.py`
- Test: `tests/generation/test_prompt_engine.py`

**Interfaces:**
- Consumes: `config.prompt_grammar.*` (Task 1).
- Produces: `generation.prompt_engine.PromptEngine().generate() -> dict` with keys `semantic_prompt`, `render_prompt`, `final_prompt`, `dna` — used by Task 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_prompt_engine.py
from generation.prompt_engine import PromptEngine
from config.prompt_grammar import THEMES


def test_generate_returns_expected_shape():
    engine = PromptEngine()

    result = engine.generate()

    assert isinstance(result, dict)
    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/test_prompt_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generation.prompt_engine'`

- [ ] **Step 3: Move and rename**

```bash
git mv core/prompt_engine_v2.py generation/prompt_engine.py
```

In `generation/prompt_engine.py`, change every occurrence of `PromptEngineV2` to `PromptEngine` (the class definition line `class PromptEngineV2:` becomes `class PromptEngine:` — no other content changes; the module docstring, all methods, `_diversity`/`_pair_memory` class attributes, and `generate()` logic stay exactly as they are today).

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/generation/test_prompt_engine.py -v`
Expected: PASS (1/1)

- [ ] **Step 5: Run full suite**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: previous results unchanged, plus `tests/generation/test_prompt_engine.py` 1/1 PASS. `core/` directory now empty.

- [ ] **Step 6: Commit**

```bash
git add generation/prompt_engine.py tests/generation/test_prompt_engine.py
git commit -m "Rename PromptEngineV2 to PromptEngine now that v1 is deleted"
```

---

### Task 8: `engine/wallpaper_engine.py` — WallpaperEngine, and rewrite `main.py`

**Files:**
- Create: `engine/wallpaper_engine.py`
- Modify: `main.py` (full rewrite)
- Test: `tests/engine/test_wallpaper_engine.py`

**Interfaces:**
- Consumes: `generation.comfy.backend.ComfyBackend` (Task 5), `generation.prompt_engine.PromptEngine` (Task 7), `engine.seed_pool.SeedPool` (Task 3), `engine.models.{GenerationRequest, EvaluationResult}` (Task 2), `database.history.HistoryRepository` (unchanged), `system.wallpaper.WallpaperService`, `system.gpu.GPUMonitor` (unchanged).
- Produces: `engine.wallpaper_engine.WallpaperEngine(backend, prompt_engine, seed_pool, history_repository, wallpaper_service, gpu_monitor, semantic_scorer_factory, aesthetic_scorer_factory).run() -> None` — the composition root (`main.py`) is the only caller.

Evaluator laziness: `semantic_scorer_factory` and `aesthetic_scorer_factory` are zero-arg callables (e.g. `SemanticPromptScorer` and `AestheticScorer` themselves, passed uncalled) that `WallpaperEngine` invokes — and therefore triggers `import evaluation.*` — only the first time `run()` reaches the evaluation step. A run that exits early (GPU busy, boot failure, generation failure) never imports `evaluation.*`.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_wallpaper_engine.py
from pathlib import Path

from engine.wallpaper_engine import WallpaperEngine
from engine.models import GenerationResult


class FakeGPUMonitor:
    def __init__(self, idle_sequence):
        self._sequence = iter(idle_sequence)

    def is_idle(self):
        return next(self._sequence)


class FakeBackend:
    def __init__(self, ready=True, result=None):
        self._ready = ready
        self._result = result
        self.generate_calls = []

    def ensure_ready(self):
        return self._ready

    def generate(self, request, seeds):
        self.generate_calls.append((request, seeds))
        return self._result


class FakePromptEngine:
    def generate(self):
        return {
            "final_prompt": "a cinematic castle",
            "semantic_prompt": "a castle",
            "dna": {"theme": "fantasy"},
        }


class FakeSeedPool:
    def __init__(self):
        self.recorded = []

    def record_result(self, seeds, score, prompt, theme):
        self.recorded.append((seeds, score, prompt, theme))


class FakeHistoryRepository:
    def __init__(self):
        self.appended = []

    def append(self, **kwargs):
        self.appended.append(kwargs)


class FakeWallpaperService:
    def __init__(self):
        self.set_calls = []

    def set_wallpaper(self, path):
        self.set_calls.append(path)


def _make_engine(gpu_monitor, backend, evaluator_factories_called):
    def semantic_factory():
        evaluator_factories_called.append("semantic")
        class _Fake:
            def score(self, path, prompt):
                return 80.0
        return _Fake()

    def aesthetic_factory():
        evaluator_factories_called.append("aesthetic")
        class _Fake:
            def score(self, path):
                return 6.0
        return _Fake()

    return WallpaperEngine(
        backend=backend,
        prompt_engine=FakePromptEngine(),
        seed_pool=FakeSeedPool(),
        history_repository=FakeHistoryRepository(),
        wallpaper_service=FakeWallpaperService(),
        gpu_monitor=gpu_monitor,
        semantic_scorer_factory=semantic_factory,
        aesthetic_scorer_factory=aesthetic_factory,
    )


def test_run_skips_when_gpu_never_idles():
    calls = []
    backend = FakeBackend()
    engine = _make_engine(FakeGPUMonitor([False] * 5), backend, calls)

    engine.run()

    assert backend.generate_calls == []
    assert calls == []


def test_run_returns_when_comfy_fails_to_boot():
    calls = []
    backend = FakeBackend(ready=False)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert backend.generate_calls == []
    assert calls == []


def test_run_returns_when_generation_fails():
    calls = []
    backend = FakeBackend(ready=True, result=None)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert len(backend.generate_calls) == 1
    assert calls == []


def test_run_happy_path_scores_persists_and_sets_wallpaper(tmp_path):
    calls = []
    result = GenerationResult(
        image_path=tmp_path / "wallpapers" / "out.png",
        used_seeds=[42, 43],
        generation_time_seconds=1.5,
    )
    backend = FakeBackend(ready=True, result=result)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert calls == ["semantic", "aesthetic"]
    assert engine.seed_pool.recorded[0][0] == [42, 43]
    combined = 0.4 * (80.0 / 100) + 0.6 * (6.0 / 10)
    assert round(engine.seed_pool.recorded[0][1], 4) == round(combined, 4)
    assert engine.history_repository.appended[0]["combined_score"] == engine.seed_pool.recorded[0][1]
    assert engine.wallpaper_service.set_calls == [result.image_path]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.wallpaper_engine'`

- [ ] **Step 3: Write the implementation**

```python
# engine/wallpaper_engine.py
"""One wallpaper-generation cycle: GPU-idle wait, generate, evaluate, persist, apply."""

from __future__ import annotations

import logging

from config.settings import GPU_IDLE_RETRIES, GPU_IDLE_WAIT_SECONDS
from engine.models import GenerationRequest


class WallpaperEngine:
    """Coordinates prompt generation, image rendering, and wallpaper updates."""

    def __init__(
        self,
        backend,
        prompt_engine,
        seed_pool,
        history_repository,
        wallpaper_service,
        gpu_monitor,
        semantic_scorer_factory,
        aesthetic_scorer_factory,
    ) -> None:
        self.backend = backend
        self.prompt_engine = prompt_engine
        self.seed_pool = seed_pool
        self.history_repository = history_repository
        self.wallpaper_service = wallpaper_service
        self.gpu_monitor = gpu_monitor
        self._semantic_scorer_factory = semantic_scorer_factory
        self._aesthetic_scorer_factory = aesthetic_scorer_factory
        self._semantic_scorer = None
        self._aesthetic_scorer = None

    def _get_semantic_scorer(self):
        if self._semantic_scorer is None:
            self._semantic_scorer = self._semantic_scorer_factory()
        return self._semantic_scorer

    def _get_aesthetic_scorer(self):
        if self._aesthetic_scorer is None:
            self._aesthetic_scorer = self._aesthetic_scorer_factory()
        return self._aesthetic_scorer

    def run(self) -> None:
        """Execute one wallpaper generation cycle."""
        try:
            if not self._wait_for_idle_gpu():
                logging.info("GPU stayed busy, skipping wallpaper generation")
                return

            if not self.backend.ensure_ready():
                logging.error("ComfyUI failed to start")
                return

            prompt_data = self.prompt_engine.generate()
            request = GenerationRequest(
                prompt=prompt_data["final_prompt"],
                dna=prompt_data["dna"],
            )

            result = self.backend.generate(request, self.seed_pool)
            if not result:
                logging.info("Wallpaper generation skipped or aborted.")
                return

            logging.info("Total generation cycle time: %.2f seconds", result.generation_time_seconds)

            semantic_score = self._get_semantic_scorer().score(
                str(result.image_path), prompt_data["semantic_prompt"]
            )
            aesthetic_score = self._get_aesthetic_scorer().score(str(result.image_path))

            semantic_norm = semantic_score / 100
            aesthetic_norm = aesthetic_score / 10
            combined_score = semantic_norm * 0.4 + aesthetic_norm * 0.6

            logging.info("Combined Score: %.2f", combined_score)

            self.history_repository.append(
                seeds=result.used_seeds,
                semantic_score=semantic_score,
                aesthetic_score=aesthetic_score,
                combined_score=combined_score,
                image_path=str(result.image_path),
                generation_time=result.generation_time_seconds,
                semantic_prompt=prompt_data["semantic_prompt"],
                dna=prompt_data["dna"],
            )

            self.seed_pool.record_result(
                seeds=result.used_seeds,
                score=combined_score,
                prompt=request.prompt,
                theme=prompt_data["dna"]["theme"],
            )

            self.wallpaper_service.set_wallpaper(result.image_path)
        except Exception as exc:
            logging.exception("Wallpaper generation cycle failed: %s", exc)
            raise

    def _wait_for_idle_gpu(self) -> bool:
        for _ in range(GPU_IDLE_RETRIES):
            if self.gpu_monitor.is_idle():
                return True
            logging.info("GPU busy, retrying in 2 minutes")
            import time
            time.sleep(GPU_IDLE_WAIT_SECONDS)
        return False
```

Note: `seed_pool.record_result` is called after `history_repository.append` — matches today's `main.py` ordering (history append happens before `seed_engine.update`). Test asserts on both, order isn't separately tested but content is.

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Python313\python.exe" -m pytest tests/engine/test_wallpaper_engine.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Rewrite `main.py` as a thin composition root**

```python
# main.py
"""Application entry point."""

from __future__ import annotations

import logging
import os

from config.paths import BEST_SEEDS_FILE, HISTORY_FILE, LOG_FILE, WORKFLOW_FILE
from config.paths import DATABASE_DIR, LOGS_DIR, WALLPAPERS_DIR
from database.history import HistoryRepository
from database.seeds import SeedRepository
from engine.seed_pool import SeedPool
from engine.wallpaper_engine import WallpaperEngine
from generation.comfy.backend import ComfyBackend
from generation.comfy.client import ComfyClient
from generation.comfy.server import ComfyServer
from generation.comfy.workflow import WorkflowManager
from generation.prompt_engine import PromptEngine
from system.file_manager import FileManager
from system.gpu import GPUMonitor
from system.wallpaper import WallpaperService


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
        force=True,
    )


def _semantic_scorer_factory():
    from evaluation.semantic_scorer import SemanticPromptScorer
    return SemanticPromptScorer()


def _aesthetic_scorer_factory():
    from evaluation.aesthetic_scorer import AestheticScorer
    return AestheticScorer()


def build_engine() -> WallpaperEngine:
    """Wire all dependencies and return a ready-to-run WallpaperEngine."""
    file_manager = FileManager()
    file_manager.ensure_directories()

    seed_pool = SeedPool(SeedRepository(BEST_SEEDS_FILE))
    prompt_engine = PromptEngine()

    workflow_manager = WorkflowManager(WORKFLOW_FILE, seed_pool)
    backend = ComfyBackend(
        client=ComfyClient(),
        server=ComfyServer(),
        workflow=workflow_manager,
        file_manager=file_manager,
    )

    return WallpaperEngine(
        backend=backend,
        prompt_engine=prompt_engine,
        seed_pool=seed_pool,
        history_repository=HistoryRepository(HISTORY_FILE),
        wallpaper_service=WallpaperService(),
        gpu_monitor=GPUMonitor(),
        semantic_scorer_factory=_semantic_scorer_factory,
        aesthetic_scorer_factory=_aesthetic_scorer_factory,
    )


def main() -> None:
    """Program entry point."""
    setup_logging()
    logging.info("Script PID: %s", os.getpid())
    logging.info("Wallpaper engine started")
    build_engine().run()


if __name__ == "__main__":
    main()
```

Note: `WallpaperApplication.__init__` previously called `self.file_manager.ensure_directories()` inside `run()`; this moves it into `build_engine()` since it's a one-time setup step, not part of the per-cycle orchestration `WallpaperEngine.run()` owns. `GeneAnalytics` is no longer imported or constructed (it was dead — see Task 1's spec cross-reference).

- [ ] **Step 6: Run full suite**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: all tests from Tasks 1-7 unchanged, plus `tests/engine/test_wallpaper_engine.py` 4/4 PASS. `tests/test_gene_analytics.py::test_trait_averages` still fails (pre-existing, untouched).

- [ ] **Step 7: Commit**

```bash
git add engine/wallpaper_engine.py main.py tests/engine/test_wallpaper_engine.py
git commit -m "Add WallpaperEngine orchestrator, rewrite main.py as a thin composition root"
```

---

### Task 9: Final cleanup and repo-wide verification

**Files:**
- Modify: none expected (verification task)
- Delete: any now-empty `core/`, `comfy/` directory remnants

**Interfaces:**
- None — this task only verifies Tasks 1-8 left no stale references.

- [ ] **Step 1: Grep for stale import paths across the whole repo**

Run: `grep -rn "core\.seed_engine\|core\.prompt_engine\|core\.clip_manager\|core\.aesthetic_scorer\|core\.semantic_scorer\|comfy\.client\|comfy\.server\|comfy\.workflow\|config\.constants\b\|config\.constants_v2\|SeedEngine\|PromptEngineV2" --include="*.py" .`
Expected: no matches (empty output). If any match appears, it's a missed reference from an earlier task — fix it now and re-run this grep.

- [ ] **Step 2: Confirm `core/` and `comfy/` are gone**

Run: `ls core/ comfy/ 2>&1`
Expected: both report "No such file or directory" (git removed their contents in Tasks 1, 3, 4, 6, 7; if either directory still exists but is empty, remove it — empty directories aren't tracked by git but may linger on disk).

- [ ] **Step 3: Run the full test suite one final time**

Run: `"C:\Python313\python.exe" -m pytest tests/ -v`
Expected: every test from Tasks 1-8 passes; only `tests/test_gene_analytics.py::test_trait_averages` fails, matching the documented pre-existing baseline.

- [ ] **Step 4: Manual end-to-end verification (not automatable in this environment)**

This plan's environment has no live ComfyUI instance or GPU to exercise. Before considering this phase done, run `"C:\Python313\python.exe" main.py` on a machine with ComfyUI installed and confirm: GPU-idle wait triggers correctly, ComfyUI boots if not running, a wallpaper generates, `data/history.json` gets a new entry with the same field shape as before this refactor, `data/best_seeds.json` gets updated, and the desktop wallpaper actually changes. Record the result in the PR description or commit message — do not mark this phase complete without it.

- [ ] **Step 5: Commit (only if Step 2 required removing lingering empty directories)**

```bash
git add -A
git commit -m "Remove empty core/ and comfy/ directories"
```

(Skip this commit if there was nothing to stage.)
