# Engine ↔ ComfyUI Seam — Design Spec

Date: 2026-09-25
Status: approved design, pre-implementation

## Priorities (read before implementing)

1. **This is a local Windows side project**, not a production/cloud service. No multi-user, no horizontal scaling, no auth, no distributed-systems concerns. Optimize for developer experience, local install, maintainability, and fun experimentation on a consumer GPU.
2. **Keep the architecture clean but deliberately avoid speculative abstractions.** An abstraction earns its place only if it solves a problem that exists today in this codebase — not a problem a hypothetical future backend/strategy/scale might have.
3. **Preserve current behavior during this phase.** Same pipeline, same constants, same output. This is a structural refactor, not a feature change.
4. **The primary architectural improvement is the Engine ↔ ComfyUI seam.** Everything else in this spec is in service of that one seam.
5. **Dataclasses are retained** (`GenerationRequest`, `GenerationResult`, `EvaluationResult`) because they solve an immediate, present-day problem: untyped dicts currently get passed through 3+ layers in `main.py` with no shape guarantee.
6. **`ComfyBackend` is the concrete boundary.** No `Protocol`/ABC for `GenerationBackend`, `BackendLifecycle`, or `GenerationStrategy` — there is exactly one backend and one strategy, and formalizing an interface for a single implementation is speculative. The boundary is enforced by import discipline (`engine/` never imports `generation/comfy/`), not by typing machinery.
7. **Directory restructuring is purposeful, not cosmetic.** Every move groups code by responsibility (what breaks together, what should be swappable together). No renames for taxonomy purity alone (e.g. `database/` stays `database/`).
8. **Out of scope for this phase:** candidate generation, new multi-dimensional scoring, scheduling/daemon mode, any UI, personalization/feedback loop. Those are separate future specs that depend on this seam existing first.

## Problem

`main.py`'s `WallpaperApplication` currently constructs and directly wires ComfyUI-specific objects (`ComfyClient`, `ComfyServer`, `WorkflowManager`) at the same level as domain objects (`SeedEngine`, `HistoryRepository`, `WallpaperService`). Concretely: `WorkflowManager` (which mutates ComfyUI workflow JSON by node ID) holds a direct reference to `SeedEngine` and calls `seed_engine.get_seed()` once per `KSampler` node it finds — meaning a ComfyUI-workflow-topology fact (how many KSamplers exist) currently dictates how many times the seed strategy gets invoked, with the domain object #having no idea this is happening. There is no code boundary that would let a second generation backend (e.g. calling Diffusers directly) be swapped in without touching seed logic, scoring, persistence, or `main.py`'s orchestration.

Verified via repo-wide grep before any deletion is proposed (see Deletions below) — nothing outside the files named as dead is dead.

## Current dependency graph

```
main.py
 ├─ comfy.client.ComfyClient
 ├─ comfy.server.ComfyServer
 ├─ comfy.workflow.WorkflowManager ──depends on──> core.seed_engine.SeedEngine
 ├─ core.prompt_engine.PromptEngine          (v1, dead branch — v2PromptEnabled always True)
 ├─ core.prompt_engine_v2.PromptEngineV2
 ├─ core.seed_engine.SeedEngine ──depends on──> database.seeds.SeedRepository
 ├─ core.semantic_scorer.SemanticPromptScorer ─┐
 ├─ core.aesthetic_scorer.AestheticScorer      ├─ both depend on core.clip_manager (eager CLIP load at import)
 ├─ database.history.HistoryRepository
 ├─ system.file_manager.FileManager
 ├─ system.gpu.GPUMonitor
 ├─ system.wallpaper.WallpaperService
 └─ analytics.gene_analytics.GeneAnalytics    (constructed, .compute_trait_score() never called)

comfy.workflow / comfy.client / comfy.server / system.gpu  ──import config.constants (infra values)
core.prompt_engine_v2 ──imports config.constants_v2
core.prompt_engine    ──imports config.constants   (dead)
```

`config.constants.py`'s infra tail (COMFY_URL, node IDs, GPU thresholds, timing) is duplicated verbatim in `config.constants_v2.py`'s tail — one canonical copy needed, not two.

## Proposed dependency graph

```
main.py ──builds──> engine.wallpaper_engine.WallpaperEngine
                        ├─ generation.comfy.backend.ComfyBackend   (concrete class, not a Protocol)
                        ├─ generation.prompt_engine.PromptEngine    (renamed from PromptEngineV2, no v1 anymore)
                        ├─ engine.seed_pool.SeedPool                (renamed from SeedEngine)
                        ├─ evaluation.semantic_scorer.SemanticPromptScorer   (constructed lazily, at first evaluation)
                        ├─ evaluation.aesthetic_scorer.AestheticScorer       (constructed lazily, at first evaluation)
                        ├─ database.history.HistoryRepository
                        ├─ system.wallpaper.WallpaperService
                        ├─ system.gpu.GPUMonitor
                        └─ system.file_manager.FileManager

generation.comfy.backend.ComfyBackend
  ├─ generation.comfy.client.ComfyClient
  ├─ generation.comfy.server.ComfyServer
  └─ generation.comfy.workflow.WorkflowManager ──calls──> a SeedPool instance's .next_seed() (duck-typed, no Protocol)
```

`engine/` never imports anything under `generation/comfy/`. Only `main.py` (composition root) and `generation/comfy/backend.py` know ComfyUI exists as a concept — everywhere else it's an opaque generation backend.

## Directory tree

```
engine/
  wallpaper_engine.py   # WallpaperEngine — was WallpaperApplication; orchestrates one cycle
  models.py               # GenerationRequest, GenerationResult, EvaluationResult (plain dataclasses)
  seed_pool.py             # SeedPool — was SeedEngine
generation/
  prompt_engine.py         # PromptEngine — was PromptEngineV2, moved + renamed, logic unchanged
  comfy/
    backend.py              # NEW — ComfyBackend, composes client+server+workflow, the only ComfyUI-aware boundary file
    client.py                # unchanged (HTTP)
    server.py                # unchanged (process lifecycle)
    workflow.py               # unchanged mutation logic; constructor takes a seed pool instead of importing SeedEngine
evaluation/
  clip_backbone.py           # was core/clip_manager.py
  aesthetic_scorer.py         # was core/aesthetic_scorer.py
  semantic_scorer.py           # was core/semantic_scorer.py
database/
  history.py                  # was database/history.py — unchanged, unmoved package name
  seeds.py                     # was database/seeds.py
system/
  gpu.py                       # unchanged
  wallpaper.py                  # unchanged
  file_manager.py                # unchanged
config/
  settings.py                     # merged infra constants — single canonical copy of COMFY_URL, node IDs, GPU/boot timings, seed pool params
  prompt_grammar.py                # was config/constants_v2.py, minus the infra tail (THEMES, MOOD_*, DiversityTracker, TraitPairMemory, etc.)
  paths.py                          # unchanged
main.py                              # thin composition root: build ComfyBackend, PromptEngine, SeedPool, evaluators, repositories → WallpaperEngine(...).run()
analytics/gene_analytics.py          # untouched, unmoved, left unwired (see Deletions)
tests/                                 # mirrors the tree above
```

`database/` keeps its current name — it stores JSON, "database" already reads as "the thing that persists our records," renaming it to `persistence/` was cosmetic and is dropped per priority 7.

## Core data shapes

Plain dataclasses, no Protocols:

```python
# engine/models.py
@dataclass
class GenerationRequest:
    prompt: str
    dna: dict[str, object]          # opaque strategy metadata; engine passes it through, doesn't interpret it

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

```python
# engine/seed_pool.py
class SeedPool:
    def next_seed(self) -> int: ...
    def record_result(self, seeds: list[int], score: float, prompt: str, theme: str) -> None: ...
```

```python
# generation/comfy/backend.py
class ComfyBackend:
    def ensure_ready(self) -> bool: ...                                  # start ComfyUI process if not running, wait for boot
    def generate(self, request: GenerationRequest, seeds: SeedPool) -> GenerationResult: ...
```

`WorkflowManager.prepare()` calls `seeds.next_seed()` once per `KSampler` node it encounters while walking the workflow JSON — this is exactly today's behavior, just inverted so the seed source is handed in rather than imported. `GenerationResult.used_seeds` reports what was actually consumed back up to the engine, which records scores against those seeds only after evaluation completes (score isn't known at generation time).

No `Protocol` classes are defined for any of the above. If a second backend or strategy is ever built, formalize the interface *then*, from two real implementations, not now from zero.

## Module responsibilities

| Module | Responsibility |
|---|---|
| `engine/wallpaper_engine.py` | One cycle: wait GPU idle → `backend.ensure_ready()` → `prompt_engine.generate()` → `backend.generate()` → evaluate (lazy-construct evaluators on first use) → `seed_pool.record_result()` → `history.append()` → `wallpaper_service.set_wallpaper()` |
| `engine/seed_pool.py` | Load historical seeds, sample top-N by score with reuse probability, else fresh random. Same algorithm as today's `SeedEngine`, renamed to match what it does (mutation is dead code today, not implemented). |
| `generation/comfy/backend.py` | NEW. Only file that translates domain `GenerationRequest` ↔ ComfyUI workflow JSON. Composes `ComfyClient` + `ComfyServer` + `WorkflowManager`. |
| `generation/comfy/{client,server,workflow}.py` | Unchanged responsibilities (HTTP calls, process lifecycle, node-JSON mutation). `WorkflowManager` constructor signature changes from taking a `SeedEngine` to taking anything with `.next_seed()`. |
| `generation/prompt_engine.py` | `PromptEngineV2`'s logic, unchanged, renamed to `PromptEngine` now that v1 is deleted. |
| `evaluation/*` | Unchanged scoring logic, relocated. Construction deferred to point-of-use inside `WallpaperEngine`, not `__init__`, so a run that never reaches evaluation never pays the CLIP/torch load cost. |
| `database/*` | Unchanged. |
| `system/*` | Unchanged. |
| `config/settings.py` | Single canonical copy of infra constants (currently duplicated across `constants.py` and `constants_v2.py` tails). |
| `config/prompt_grammar.py` | v2.3 prompt-domain data and helpers — pure data/logic, no infra constants mixed in. |

## Deletions (verified by repo-wide grep, not filename guess)

- `core/prompt_engine.py` — only referenced by its own two test files; nothing else imports v1 `PromptEngine`.
- `tests/test_prompt_engine.py`, root `test_prompt_engine.py` — test the dead v1 engine.
- `config/constants.py` — its prompt-domain data (`PROMPT_DICT`, `ATMOSPHERE`, `CAMERA*`, `DETAIL`, `*_LIGHT`, v1 `SEMANTIC_TEMPLATES`/`RENDER_TEMPLATES`) is consumed only by the dead v1 engine; its infra tail is a verbatim duplicate of `constants_v2.py`'s tail and gets merged into `config/settings.py` instead.
- `v2PromptEnabled` flag and its `else` branch in `main.py`.
- Dead `PromptEngine` (v1) import in `main.py`.
- Unused `GeneAnalytics(...)` construction + import in `main.py` — the module `analytics/gene_analytics.py` itself and its test stay untouched; it's just not wired into the live path, same as today, but without a dead reference sitting in `WallpaperApplication.__init__`.

## Moves & renames

Covered in the directory tree. Renames, with justification for each (per priority 7 — no cosmetic renames):

- `SeedEngine` → `SeedPool`: traced the actual algorithm (load history → sort by score → sample from top-`BEST_SEED_LIMIT` with `BEST_SEED_REUSE_PROBABILITY`, else fresh random; mutation code is commented out and dead). "Evolution" overstates what happens today. If mutation is reintroduced later it becomes a strategy layered on the pool, not a rename back.
- `PromptEngineV2` → `PromptEngine`: v1 is deleted in this same phase, so "V2" no longer disambiguates anything — it would just be a stale version marker on the only engine that exists.
- Everything else (`WallpaperService`, `ComfyClient`, `ComfyServer`, `WorkflowManager`, `HistoryRepository`, `FileManager`, `GPUMonitor`, `SeedRepository`) keeps its name — none are misleading, only relocated.

## Migration sequence

1. Scaffold new package directories (`engine/`, `generation/`, `generation/comfy/`, `evaluation/`), empty `__init__.py`s. Nothing deleted yet.
2. Add `engine/models.py` (three dataclasses) and `engine/seed_pool.py` (`SeedPool`, moved + renamed from `core/seed_engine.py`).
3. Move `comfy/*` → `generation/comfy/*`. Change `WorkflowManager.__init__` to accept a seed-pool-like object instead of importing `SeedEngine`. Add `generation/comfy/backend.py::ComfyBackend` wiring `ComfyClient`+`ComfyServer`+`WorkflowManager` behind `ensure_ready()`/`generate()`.
4. Move `core/prompt_engine_v2.py` → `generation/prompt_engine.py`, rename class `PromptEngineV2` → `PromptEngine`. No logic change.
5. Move `core/{clip_manager,aesthetic_scorer,semantic_scorer}.py` → `evaluation/`.
6. Split `config/constants.py` + `config/constants_v2.py` → `config/settings.py` (infra constants, one copy) + `config/prompt_grammar.py` (prompt-domain data). Delete both originals.
7. Rewrite `main.py` as a thin composition root: build `ComfyBackend`, `PromptEngine`, `SeedPool`, `HistoryRepository`, `WallpaperService`, `GPUMonitor`, `FileManager`, pass to `WallpaperEngine`, call `.run()`. Import `evaluation.*` lazily inside `WallpaperEngine`'s evaluation step, not at module top level, so the CLIP/torch load genuinely only happens when a cycle reaches evaluation.
8. Delete dead files (see Deletions).
9. Update `tests/` imports to new module paths (notably `tests/test_seed_engine.py`, `tests/test_history.py` reference old paths directly).
10. Run full test suite. Run one real end-to-end generation manually (GPU idle wait → ComfyUI boot/generate → score → history append → wallpaper set) and confirm identical behavior to pre-refactor: same prompt→workflow mapping, same constants, same output file naming.

## Risks

- **Constants merge drift**: `config/settings.py` must carry the exact same numeric values as both old files' infra tails. A transcription slip silently changes GPU-idle-wait, ComfyUI boot-retry, or seed-reuse-probability behavior.
- **`WorkflowManager` signature change**: its only caller (`ComfyBackend`, new) and its only existing test must be updated in the same commit or a test goes stale silently.
- **Lazy-load only helps if the import itself is deferred**: `core/clip_manager.py` calls `clip.load(...)` at module import time, not at class-instantiation time. Deferring `SemanticPromptScorer()`/`AestheticScorer()` construction only avoids the cost if the `import evaluation.*` statement is also inside the deferred code path (e.g. inside `WallpaperEngine`'s evaluation method), not at the top of `main.py` or `engine/wallpaper_engine.py`. Flagging explicitly so this isn't implemented as a half-fix.
- **Opaque `dna` dict** still crosses `PromptEngine` → `ComfyBackend` → `WallpaperEngine` → `SeedPool`/`HistoryRepository` untyped. Deliberate for this phase — a typed schema is premature until a future scoring redesign needs to interpret specific fields.
- **Test breakage surface**: `tests/test_seed_engine.py` and `tests/test_history.py` import old module paths directly; they need path/name updates, not just re-runs.
- **Behavior-preservation is the acceptance bar** for this phase — no new features, no scoring changes, no candidate logic. Any test or manual-run divergence from pre-refactor output is a regression to fix, not a design decision to revisit.
