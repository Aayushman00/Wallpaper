# Taste Learning — Design Spec

**Goal:** Make "evolves toward what you like" real. Record each like/dislike against the rated image's prompt traits (`dna`), then bias future prompt generation toward traits you rate well and away from traits you rate poorly — gently, with an exploration floor, and safely with sparse ratings.

**Why:** Today a like/dislike only rescales the stored score of the image's seeds in `best_seeds.json`. A seed offset (`±BEST_SEED_MUTATION_RANGE`) does not preserve any visual trait, so that signal barely steers anything. `GeneAnalytics` averages CLIP `combined_score` per trait and is unused; it measures CLIP's taste, not the user's. The prompt traits (`dna`) are what actually carry visual character.

**Purpose (agreed):** daily personal use on one Windows machine. Not a portfolio or open-source release.

**Non-goals (separate future specs — do not build here):**
- Preference model (logistic regression, CLIP-embedding based) or Thompson sampling. `compute_taste` is a single pure function so either can replace it later.
- Time decay of old ratings.
- A taste report UI or CLI.
- Weather/sun prompting and the tray app (separate sub-projects).
- Changing the existing seed-rescoring behavior of like/dislike.

**Tech stack:** unchanged. No new dependencies.

**Builds on:** `docs/superpowers/specs/2026-09-26-wallpaper-evolution-daemon-design.md` (branch `feature/evolution-daemon`: `WallpaperDaemon`, `current_state.json`, `PromptEngine.generate(context=...)`).

## Global Constraints

- No new dependencies; local Windows side project; no ABC/Protocol for single implementations.
- `PromptEngine.generate()` with no arguments, and with `context` only, behaves exactly as before; `tests/generation/test_prompt_engine.py` passes unmodified.
- `WallpaperEngine.run()` keeps working with fakes whose `generate()` takes no arguments: `context`/`taste` are passed only when truthy.
- Existing like/dislike seed-rescoring (`SeedPool.rate_current`) is unchanged and still runs.
- `history.json` entries without `rating` are valid (unrated); no migration.
- A taste failure must never block or kill a generation cycle.
- Test runner: `"C:\Python313\python.exe" -m pytest <path> -v`.

## Architecture

```
hotkey like/dislike ──► WallpaperDaemon._rate
                          ├─ SeedPool.rate_current(seeds, liked)        (unchanged)
                          └─ HistoryRepository.set_rating(image_path, ±1)   (new)

each cycle: WallpaperDaemon.run_cycle
   taste = compute_taste(history.load())      # pure, analytics/taste_model.py
   engine.run(context=..., taste=taste)
     └─ PromptEngine.generate(context=..., taste=taste)
          └─ _apply_taste(pool, trait) multiplies weights at each trait pick
```

History is the single source of truth: taste is recomputed from `history.json` each cycle (hundreds of entries — trivial cost). There is no second taste file to drift out of sync.

## Components

| Module | Change |
|---|---|
| `database/history.py` | `set_rating(image_path, rating) -> bool`; `RLock` around `load`/`append`/`set_rating`. |
| `analytics/taste_model.py` (new) | `compute_taste(history) -> dict[str, dict[str, float]]`, pure, no I/O. |
| `generation/prompt_engine.py` | `generate(context=None, taste=None)`; `_apply_taste(items, trait)`; weighted theme pick. |
| `engine/wallpaper_engine.py` | `run(context=None, taste=None)`; passes each to `generate()` only when truthy. |
| `engine/wallpaper_daemon.py` | `_rate` also calls `set_rating`; `run_cycle` computes taste (failure → `None`) and logs top boosted/penalized values. |
| `config/settings.py` | `TASTE_PRIOR = 3`, `TASTE_MIN = 0.4`, `TASTE_MAX = 2.0`. |
| `tests/test_gene_analytics.py` | Fix fixture key `"score"` → `"combined_score"` (baseline failure was a test bug). |

## Data Shapes

`history.json` entry gains one optional field:
```json
{ "...": "existing fields", "rating": 1 }
```
`1` = liked, `-1` = disliked, absent = unrated. Latest rating on an image replaces the earlier one.

`compute_taste` output (omitted values mean 1.0):
```json
{ "mood": {"eerie and abandoned": 1.57, "serene": 0.75}, "light_time": {"golden hour": 1.25} }
```

## `HistoryRepository.set_rating`

`set_rating(image_path: str, rating: int) -> bool`: under the lock, load; find the **newest** entry whose `image_path == image_path`; set `entry["rating"] = rating`; save atomically (same tmp + fsync + replace as `append`); return `True`. If no entry matches, return `False` and write nothing. Rating the same image twice stores one value (idempotent — unlike the seed multiplier, which compounds).

The `RLock` guards `load`, `append`, and `set_rating` because the hotkey thread (`set_rating`, `revert`'s read) and the scheduler thread (`append`) both touch the file; on Windows an unguarded `replace` during a read raises `PermissionError`.

## `compute_taste`

Pure function over history entries.

- Consider only entries with `rating` in `{1, -1}`. Unrated entries are ignored (not counted as neutral).
- For each string-valued `dna` item `(trait, value)`: `likes`, `dislikes`, `n = likes + dislikes` over rated entries containing it.
- `multiplier = clamp(1 + (likes - dislikes) / (n + TASTE_PRIOR), TASTE_MIN, TASTE_MAX)`.
- Non-string `dna` values (e.g. `scene_density_score`) are skipped.
- Values never rated are absent from the output (treated as 1.0).

Properties: one like ≈ 1.25×, four likes ≈ 1.57×, one dislike = 0.75×, many dislikes floor at `TASTE_MIN` (rarely chosen, never impossible). The prior shrinks thin data toward 1.0.

`# ponytail: no time decay — add if taste drift matters.`

## Applying taste in `PromptEngine`

`_apply_taste(items, trait)` returns items with `weight * taste.get(trait, {}).get(item["label"], 1.0)`; returns `items` unchanged when `taste` is falsy; never mutates its input. It runs **after** hard compatibility filters, diversity decay, density guard and context bias, so effects multiply and incompatible combinations are never revived.

Hooked picks (trait key = existing `dna` key): `theme` (today uniform `random.choice`; becomes weighted), `subject` (weights list is parallel to `subjects`; multiply per label), `location`, `environment`, `light_time`, `light_quality`, `mood`, `framing`, `lens`, `camera_angle`, `render_medium`, `quality_marker`, `environmental_condition`.

`taste=None` or empty → identical to current behavior.

## Daemon Flow

1. `like()`/`dislike()`: if `state` exists → `seed_pool.rate_current(...)` (as today) then `history_repository.set_rating(state["image_path"], ±1)`. If `set_rating` returns `False`, log it; the seed rescoring still applied. No state → no-op as today.
2. `run_cycle()`: inside the existing `try`, `taste = compute_taste(history_repository.load())` wrapped so any exception logs and yields `taste = None`; call `engine.run(context=..., taste=taste)`; log the 3 most boosted and 3 most penalized (trait, value, multiplier) at INFO.

## Error Handling

- History unreadable/corrupt at taste time → log, `taste = None`, cycle proceeds.
- `set_rating` image not found (history trimmed/edited) → log, return `False`, no crash.
- Rating after revert → `current_state` already points at the reverted image (daemon spec fix), so the rating lands on what is on screen.
- Quarantined images are never in `current_state`, so they cannot be rated.

## Testing

- `compute_taste`: empty history; unrated ignored; 1 like = 1.25; 4 likes ≈ 1.57; 1 dislike = 0.75; many dislikes clamp to `TASTE_MIN`; many likes never exceed `TASTE_MAX`; non-string dna values skipped; mixed like/dislike on same value nets out.
- `HistoryRepository.set_rating`: sets on the newest matching entry only; replaces an earlier rating; returns `False` and leaves file unchanged when not found; concurrent `append` + `set_rating` lose no entries.
- `PromptEngine._apply_taste`: no-op without taste; boosts/penalizes by label; unknown labels untouched; does not mutate input; `generate(taste=...)` returns the expected shape; **guard test:** every trait name hooked in `generate` is a key of the returned `dna` (a typo would silently disable steering).
- `WallpaperEngine.run`: passes `taste` only when truthy; old no-arg `generate()` fakes still work.
- Daemon: like/dislike write the rating on the current image and still call `rate_current`; rating after revert targets the reverted image; `run_cycle` passes taste; a raising `history.load()` for taste yields `taste=None` and the cycle still runs; not-found rating logs without crashing.
- Manual: rate 5–10 wallpapers, restart, confirm the boosted/penalized log lines match what you rated and that generated traits shift over a few cycles.

## Review Focus

- **Silent no-op steering:** a trait key that doesn't match a `dna` key (typo) disables that trait's steering with no error — pinned by the guard test.
- **Rating lost or doubled:** rating the same image twice must store one value; rating an image missing from history must not crash or corrupt.
- **Sparse data over-steering:** one or two ratings must not collapse variety — shrinkage and `TASTE_MIN` floor pinned by tests.
- **Taste failure blocks generation:** a corrupt history must still produce a wallpaper.
- **Concurrent history writes:** hotkey-thread rating vs scheduler append must lose nothing.
