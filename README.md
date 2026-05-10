# Wallpaper Change (ComfyUI-powered Automatic Wallpaper Engine)

A Windows wallpaper automation tool that generates high-quality images using ComfyUI, scores and stores favorites, and updates desktop wallpaper automatically when GPU is idle.

## ⭐ Key features

- Uses prompt generation (`core/prompt_engine.py`) with style
- Controlled ComfyUI workflow execution (`comfy/workflow.py`) with injected prompt and seeds
- GPU idle detection via `nvidia-smi` (`system/gpu.py`) to avoid collisions
- ComfyUI child process lifecycle management (`comfy/server.py`)
- Wallpaper application through Windows API (`system/wallpaper.py`)
- Matte history and seed persistence in JSON (`database/history.py`, `database/seeds.py`)
- Light scoring heuristic (`core/scoring.py`) for best-seed evolution

## 🧱 Repo structure

- `main.py`: orchestrator (`WallpaperApplication`) and run entry point
- `config/`: constants and paths
- `core/`: prompt, scoring, and seed evolution logic
- `comfy/`: ComfyUI REST client, server, workflow management
- `system/`: filesystem, GPU, and wallpaper integrations
- `database/`: persistence for seeds/history
- `wallpaper.json`: ComfyUI workflow source

## 🔧 Prerequisites

- Windows 10/11
- Python 3.11+ (or as packaged in `ComfyUI_windows_portable/python_embeded`)
- ComfyUI portable installed under `ComfyUI_windows_portable`
- `nvidia-smi` available in PATH for GPU monitoring
- `requests` package

## 📦 Install

```powershell
pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cu128
```

(If this repo doesn’t include `requirements.txt`, install at least `requests` explicitly.)

## ▶️ Run

```powershell
python main.py
```

This will:
1. Ensure directories (`logs/`, `wallpapers/`, `database/`) exist
2. Wait for GPU idle
3. Start ComfyUI if needed
4. Generate a prompt and render through ComfyUI API
5. Move output image to `wallpapers/` with timestamped filename
6. Score prompt and append history
7. Set desktop wallpaper

## 🛠 Configuration

- Edit `config/constants.py` for all generative and timing settings
- `COMFY_URL` and workflow-related IDs are in `config/constants.py`
- Persisted files in `config/paths.py`:
  - `DATABASE_DIR/history.json`
  - `DATABASE_DIR/best_seeds.json`

## 🔁 Workflow customization

- `wallpaper.json` defines the ComfyUI node graph
- `WorkflowManager.prepare()` injects prompt and seed into `WORKFLOW_PROMPT_NODE_ID`

## 🧪 Runtime behavior

- retries for GPU and ComfyUI startup
- generation timeout in `config/constants.GENERATION_TIMEOUT_SECONDS`
- history polling interval in `config/constants.HISTORY_POLL_SECONDS`

## 🐛 Troubleshooting

- If wallpaper generation hangs, confirm ComfyUI process is responsive at `http://127.0.0.1:8188`.
- If GPU check always fails, run `nvidia-smi` manually and validate output.
- Invalid JSON in `database/*.json` can cause resets; fix corruption or delete and retry.

## 🛡 Safety notes

- This project currently assumes Windows in `system/wallpaper.py`.
- Add error-handling for `ctypes.windll.user32.SystemParametersInfoW` and unsupported platforms.

## ✅ Suggestion for enhancement

- Add a scheduler/daemon mode (e.g., run every hour)
- Convert JSON persistence into SQLite for scale
- Limit history file growth and prune old entries
- Add robust error handling and alpha feature flags

---

Maintained by an AI-driven review chain. Feel free to adapt to your workflow and package style preferences.
