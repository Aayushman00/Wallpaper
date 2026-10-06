# Wallpaper Evolution Daemon — Design Spec

**Goal:** Turn the one-shot `main.py` script into a resident background daemon that (1) auto-generates a new wallpaper on a timer, (2) lets the user rate the current wallpaper with global hotkeys, feeding that rating back into seed selection as an explicit fitness signal alongside the existing CLIP-based `combined_score`, (3) actually applies the seed mutation `config/settings.py` already declares but never uses, and (4) adds three small independent quality/context gates. This is the visible, "never the same wallpaper twice, and it evolves toward what you actually like" feature the project was started for.

**Non-goals (deferred to future specs — do not build here):**
- Concurrent lineages (separate evolving populations per theme, cross-breeding).
- A local dashboard/viewer for score trends or the lineage tree.
- Weekly diary collage generation.
- Windows lock-screen sync.
- Weather-based prompting (needs a network API + credentials — out of scope for "local, no new deps").
- Any lineage *visualization* — this spec only stores `parent_seed`/`generation` fields; viewing them is a future spec's job.

**Tech stack:** unchanged (Python 3.13, pytest, requests, torch/clip). No new third-party dependencies — hotkeys and focus detection use `ctypes` against `user32.dll` (stdlib), matching the existing `system/wallpaper.py` pattern.

## Global Constraints

- Local Windows side project — no Protocol/ABC interfaces for single-implementation boundaries.
- No new dependencies. Hotkey listening and fullscreen detection go through `ctypes`/`user32`, the same approach `system/wallpaper.py` already uses for `SystemParametersInfoW`.
- Preserve `WallpaperEngine.run()`'s existing one-cycle behavior and its existing tests (`tests/engine/test_wallpaper_engine.py`) — the daemon wraps and schedules it, it does not rewrite it.
- `SeedPool.record_result`'s existing signature and ranking behavior (top `BEST_SEED_LIMIT` by score) stays; new fields (`parent_seed`, `generation`) are additive to the record dict, not replacements.
- Test runner: `"C:\Python313\python.exe" -m pytest <path> -v`.
- Baseline: `tests/test_gene_analytics.py::test_trait_averages` fails on main already (pre-existing, out of scope, do not fix).

## Architecture

One resident process, two threads, no IPC:

```
engine/wallpaper_daemon.py::WallpaperDaemon
├── scheduler thread: loop { wait GENERATION_INTERVAL (gated by focus-assist) → engine.run() → persist current_state }
└── hotkey thread: Win32 message pump (RegisterHotKey) → dispatch to daemon methods
```

The daemon holds "what's currently displayed" as in-memory state, mirrored to `data/current_state.json` on every successful cycle so a reboot mid-display doesn't strand the hotkey handlers with nothing to rate. `main.py` becomes the composition root for the daemon instead of for a single `WallpaperEngine.run()` call.

### Component responsibilities

| Module | Responsibility |
|---|---|
| `engine/wallpaper_daemon.py` (new) | Owns both threads, current-state persistence, hotkey dispatch, focus-assist gating of the schedule. |
| `engine/seed_pool.py` (modified) | Real mutation on reuse; `parent_seed`/`generation` tracking; new `rate_current` and `penalize` methods. |
| `engine/wallpaper_engine.py` (modified) | Quality-floor check after scoring; returns enough info (which seed records were written) for the daemon to point `current_state` at them. |
| `generation/context_signals.py` (new) | `get_time_of_day()`, `get_season()` — pure functions, no I/O beyond the system clock. |
| `generation/prompt_engine.py` (modified) | Accepts optional context signals, nudges lighting/mood weighting. |
| `system/focus_assist.py` (new) | `is_fullscreen_app_active() -> bool` via `user32`. |
| `system/hotkeys.py` (new) | Thin wrapper around `RegisterHotKey`/`GetMessage`/`UnregisterHotKey` — the only file that touches the Win32 hotkey API, mirroring how `generation/comfy/` is the only file touching ComfyUI's API. |
| `config/settings.py` (modified) | New constants (below). |

## New Settings Constants (`config/settings.py`)

- `GENERATION_INTERVAL_SECONDS` — scheduler's normal wait between cycles (the "auto-generate on a timer" cadence). Exact value is a user preference to confirm at plan time, not a design decision — default suggestion `14400` (4 hours).
- `AESTHETIC_QUALITY_FLOOR = 4.0`
- `FOCUS_ASSIST_RECHECK_SECONDS = 300`
- `SEED_RATING_LIKE_MULTIPLIER = 1.5`
- `SEED_RATING_DISLIKE_MULTIPLIER = 0.3`

## Data Flow

1. Daemon starts: loads `data/current_state.json` if present (so hotkeys work immediately on restart), registers hotkeys, starts scheduler thread.
2. Scheduler thread: sleeps `GENERATION_INTERVAL_SECONDS`; before running, calls `focus_assist.is_fullscreen_app_active()` — if true, sleeps `FOCUS_ASSIST_RECHECK_SECONDS` and checks again instead of running.
3. When clear to run: calls `context_signals.get_time_of_day()`/`get_season()`, passes them into `prompt_engine.generate(context=...)`, then `WallpaperEngine.run()` as today, except:
   - After scoring, if `aesthetic_score < AESTHETIC_QUALITY_FLOOR`: log history with `quarantined: True`, call `seed_pool.penalize(used_seeds)` instead of `record_result`, skip `wallpaper_service.set_wallpaper` (previous image stays), skip updating `current_state.json`.
   - Otherwise: `record_result` as today (now also writing `parent_seed`/`generation` per seed, sourced from `SeedPool.next_seed()`'s return), `set_wallpaper`, and daemon writes `current_state.json` with the new seeds/image/generation.
4. Hotkey thread receives an event, calls the matching daemon method:
   - Like → `seed_pool.rate_current(liked=True)` (`SEED_RATING_LIKE_MULTIPLIER` on current record's stored score).
   - Dislike → `seed_pool.rate_current(liked=False)` (`SEED_RATING_DISLIKE_MULTIPLIER`).
   - Generate-next → interrupts the scheduler's sleep and runs a cycle immediately, bypassing focus-assist (explicit user intent overrides the gate).
   - Revert → reads the second-to-last non-quarantined `history.json` entry's `image_path`, calls `wallpaper_service.set_wallpaper` directly (does not touch scoring/seed_pool — a revert is a display choice, not new fitness data).
5. If no `current_state.json` exists yet (first run, or last cycle was quarantined) and a rating hotkey fires: log and no-op.

## Data Shapes

`data/best_seeds.json` record, extended:
```json
{
  "seed": 123456,
  "score": 0.62,
  "sampler_index": 0,
  "prompt": "...",
  "theme": "fantasy",
  "parent_seed": 98765,
  "generation": 3
}
```
`parent_seed` is `null` and `generation` is `0` for a fresh random seed.

`data/current_state.json` (new file):
```json
{
  "seeds": [123456, 654321],
  "image_path": "wallpapers/out.png",
  "generation": 3
}
```

`history.json` entries gain one new optional field: `"quarantined": true` (omitted/absent for normal entries — no migration needed for old records, `dict.get("quarantined", False)` at every read site).

## `SeedPool` Changes

- `next_seed()`: when the reuse branch fires, instead of `return random.choice(top_candidates)["seed"]`, mutate: `parent = random.choice(top_candidates); mutated = parent["seed"] + random.randint(-BEST_SEED_MUTATION_RANGE, BEST_SEED_MUTATION_RANGE); return mutated, parent["seed"], parent["generation"] + 1`. Fresh-random branch returns `(seed, None, 0)`. Return type changes from `int` to a 3-tuple — this is the one call-site-visible interface change; `WorkflowManager.prepare` (Task 4's duck-typed consumer) is updated to unpack it.
- `record_result(seeds, lineage, score, prompt, theme)`: `lineage` is the list of `(parent_seed, generation)` pairs `next_seed()` returned alongside each seed, zipped in to populate the two new fields per record.
- New `rate_current(seeds: list[int], liked: bool) -> None`: loads records, finds ones whose `seed` is in `seeds`, multiplies `score` by `SEED_RATING_LIKE_MULTIPLIER` (liked) or `SEED_RATING_DISLIKE_MULTIPLIER` (disliked), re-saves. No cap — ranking is relative, not absolute.
- New `penalize(seeds: list[int]) -> None`: same lookup, but used for quarantined generations — sets `score` to `0.0` outright rather than multiplying (a quarantined image failed the quality floor entirely; it shouldn't survive as a breeding parent at any multiplier).

## `WorkflowManager` Change (Task 4 follow-up)

`prepare()` currently calls `self.seeds.next_seed()` expecting an `int`. It now expects the 3-tuple `(seed, parent_seed, generation)`, uses `seed` for the workflow JSON exactly as before, and collects the `(parent_seed, generation)` pairs into a `used_lineage` list returned alongside `used_seeds` — `prepare()`'s return type becomes `tuple[dict, list[int], list[tuple[int | None, int]]]`. `ComfyBackend.generate()` and `GenerationResult` both gain this third piece so it reaches `WallpaperEngine` for `record_result`.

## Quality Floor

- `config/settings.py`: `AESTHETIC_QUALITY_FLOOR = 4.0` (aesthetic scores run 0–10; picked as "below the midpoint of the scale is not worth displaying" — tunable, not load-bearing on other logic).
- Lives entirely inside `WallpaperEngine.run()`'s existing scoring block — no new module.

## Focus-Assist

- `system/focus_assist.py::is_fullscreen_app_active() -> bool`: `user32.GetForegroundWindow()`, `user32.GetWindowRect()`, compare to `user32.GetSystemMetrics(SM_CXSCREEN)`/`SM_CYSCREEN`. Returns `False` (i.e. "safe to run") on any API failure — same fail-open-to-busy-but-not-blocking philosophy as `GPUMonitor.is_idle()`'s fail-to-busy on error, inverted: here we fail toward *not* blocking generation indefinitely, since staying on the last wallpaper forever if the API misbehaves is worse than an occasional generation while a borderline window is focused.
- `config/settings.py`: `FOCUS_ASSIST_RECHECK_SECONDS = 300`.

## Context-Aware Prompting

- `generation/context_signals.py`: `get_time_of_day() -> str` (`"morning"`/`"afternoon"`/`"evening"`/`"night"` from `datetime.now().hour`), `get_season() -> str` (`"winter"`/`"spring"`/`"summer"`/`"autumn"` from `datetime.now().month`). Pure, no I/O, trivially testable by injecting a fixed hour/month.
- `generation/prompt_engine.py::PromptEngine.generate()` gains an optional `context: dict | None = None` parameter (default `None` preserves today's exact random behavior — `tests/generation/test_prompt_engine.py` keeps passing unmodified). When provided, it nudges the weighted choice over `LIGHTING_TIME` entries in `config/prompt_grammar.py` toward context-compatible values (using the existing `is_lighting_compatible` table) rather than picking uniformly — a soft bias, not a filter, so variety is preserved.
- The daemon is the only caller that passes `context`; `main.py`'s existing one-shot path (if kept) and all current tests call `generate()` with no arguments and are unaffected.

## Hotkeys

`system/hotkeys.py` wraps `RegisterHotKey`/`GetMessage`/`UnregisterHotKey`, running its message pump on the daemon's hotkey thread:

| Hotkey | Action |
|---|---|
| `Ctrl+Alt+Up` | Like current |
| `Ctrl+Alt+Down` | Dislike current |
| `Ctrl+Alt+Right` | Generate next now (bypasses focus-assist) |
| `Ctrl+Alt+Left` | Revert to previous wallpaper |

If `RegisterHotKey` fails for any binding (combo already claimed by another app), log the error and continue — the scheduler thread is unaffected, the daemon degrades to "auto-generation only" rather than crashing.

## Error Handling

- No `current_state.json` and a rating/revert hotkey fires → log, no-op.
- `RegisterHotKey` failure → log, that binding is skipped, others still attempt registration.
- Revert with no prior non-quarantined history entry → log, no-op.
- Quarantined generation → previous wallpaper stays displayed; `current_state.json` is not updated (so a like/dislike immediately after a quarantine still rates the last *displayed* image, not the quarantined one).
- All existing `WallpaperEngine.run()` error handling (GPU never idle, ComfyUI boot failure, generation failure) is unchanged — the daemon's scheduler thread just calls `run()` in a loop; a single cycle's exception is logged and the loop continues to the next scheduled attempt rather than killing the daemon (`run()` currently re-raises on unexpected exceptions — the daemon's scheduler loop wraps each `run()` call in a try/except that logs and continues, since a resident process cannot let one bad cycle kill the whole daemon).

## Testing

- `SeedPool.next_seed()` mutation: fake repository with a known top seed, assert mutated value is within `±BEST_SEED_MUTATION_RANGE`, `parent_seed`/`generation` correct; fresh-random branch returns `(seed, None, 0)`.
- `SeedPool.rate_current`/`penalize`: fake repository, assert score multiplier/zeroing applied only to matching seeds.
- `WorkflowManager.prepare`: update existing fake seed source to return the 3-tuple; assert `used_lineage` shape.
- `ComfyBackend.generate`: assert `GenerationResult` carries lineage through.
- `WallpaperEngine.run()`: new test cases for quality-floor quarantine (aesthetic score below floor → `set_wallpaper` not called, `penalize` called instead of `record_result`) and for `context` being passed through to `prompt_engine.generate()` when provided.
- `context_signals`: pure function tests with an injected/mocked clock — assert hour/month boundaries map to the right bucket.
- `focus_assist.is_fullscreen_app_active` and `system/hotkeys.py`'s message pump are not unit-testable (real Win32 window state / blocking message loop) — manual verification step, same treatment as the existing ComfyUI e2e check in Task 9 of the prior plan: run the daemon, alt-tab into a fullscreen app during a scheduled window and confirm the cycle defers, press each hotkey and confirm the expected effect.

## Review Focus

- **Quarantine doesn't silently corrupt `current_state`**: a quarantined cycle must leave `current_state.json` pointing at the previously-displayed image, not the quarantined one — a like/dislike right after a quarantine must rate the right image.
- **Mutation return-type change ripple**: every caller of `SeedPool.next_seed()` (currently just `WorkflowManager.prepare`) must be updated in the same task that changes the return type — a partial update would silently break seed injection into the workflow JSON.
- **Fail-open on focus-assist API errors**: if `user32` calls raise or return garbage, the daemon must still eventually generate, not wedge on "always fullscreen."
- **Daemon survives a single bad cycle**: an exception inside one scheduled `run()` must not kill the scheduler thread — the next scheduled cycle must still fire.
