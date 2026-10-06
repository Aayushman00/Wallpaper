# Wallpaper Change (ComfyUI-powered Automatic Wallpaper Engine)

A Windows wallpaper daemon that generates images with ComfyUI, scores them, learns your taste from
likes/dislikes, and swaps the desktop wallpaper on a schedule when the GPU is idle.

## ⭐ Key features

- Procedural SDXL prompt generation with 3 themes (`fantasy`, `cyberpunk`, `space`) (`generation/prompt_engine.py`, grammar in `config/prompt_grammar.py`)
- Time-of-day / season lighting bias (`generation/context_signals.py`)
- ComfyUI workflow execution and server lifecycle (`generation/comfy/`)
- Aesthetic + semantic (CLIP) scoring; low scorers are quarantined (`evaluation/`)
- Seed pool with mutation, lineage, and like/dislike boosting (`engine/seed_pool.py`)
- Taste learning from ratings steers future prompts (`analytics/taste_model.py`)
- Resident daemon with global hotkeys and fullscreen-app deferral (`engine/wallpaper_daemon.py`, `system/hotkeys.py`, `system/focus_assist.py`)
- GPU idle detection via `nvidia-smi` (`system/gpu.py`); wallpaper set via Windows API (`system/wallpaper.py`)
- JSON persistence for history and seeds (`database/`)

## 🧱 Repo structure

- `main.py`: entry point, starts the daemon
- `config/`: settings (`settings.py`), paths, prompt grammar
- `engine/`: `WallpaperEngine` (one cycle), `WallpaperDaemon` (scheduler + hotkeys), `SeedPool`, models
- `generation/`: prompt engine, context signals, ComfyUI client/server/workflow/backend
- `evaluation/`: aesthetic and semantic scorers, CLIP backbone
- `analytics/`: gene analytics, taste model
- `system/`: GPU, wallpaper, file manager, hotkeys, focus-assist
- `database/`: history and seed repositories
- `wallpaper.json`: ComfyUI workflow source
- `tests/`: pytest suite

## 🔧 Prerequisites

- Windows 10/11
- Python 3.11+
- ComfyUI portable installed under `ComfyUI_windows_portable`
- `nvidia-smi` in PATH
- Packages in `requirements.txt` (torch, transformers, Pillow, requests, ...)

## 📦 Install

```powershell
pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cu128
```

## ▶️ Run

```powershell
python main.py
```

Tests: `python -m pytest`

Each cycle:
1. Wait for GPU idle (and for no fullscreen app)
2. Start ComfyUI if needed
3. Generate a prompt (context + learned taste) and render through the ComfyUI API
4. Score the image; quarantine it if below `AESTHETIC_QUALITY_FLOOR`
5. Move output to `wallpapers/`, append history, update the seed pool
6. Set desktop wallpaper

## 🛠 Configuration

- `config/settings.py`: ComfyUI URL and node IDs, GPU/timing settings, seed pool, daemon interval, taste bounds
- `config/paths.py`: persisted files (history, best seeds, current state)

## 🐛 Troubleshooting

- Generation hangs: confirm ComfyUI responds at `http://127.0.0.1:8188`.
- GPU check always fails: run `nvidia-smi` manually and validate output.
- Invalid JSON in `database/*.json` can cause resets; fix or delete and retry.
- Windows only: `system/wallpaper.py` uses `ctypes.windll`.

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

### Taste learning

Likes (`Ctrl+Alt+Up`) and dislikes (`Ctrl+Alt+Down`) are recorded on the rated image's history entry.
Each cycle, traits (theme, mood, lighting, framing, ...) you rate well get a gentle weight boost and
traits you rate poorly a gentle penalty (bounded to `TASTE_MIN`..`TASTE_MAX`, shrunk toward neutral when
you have few ratings, never excluded). The log shows `Taste boosted: ...` / `Taste penalized: ...` lines.
