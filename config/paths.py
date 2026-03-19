"""Filesystem paths used by the application."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_FILE = ROOT_DIR / "wallpaper.json"
LOGS_DIR = ROOT_DIR / "logs"
WALLPAPERS_DIR = ROOT_DIR / "wallpapers"
DATABASE_DIR = ROOT_DIR / "database"
LOG_FILE = LOGS_DIR / "wallpaper_engine.log"
HISTORY_FILE = DATABASE_DIR / "history.json"
BEST_SEEDS_FILE = DATABASE_DIR / "best_seeds.json"

COMFY_PORTABLE_DIR = ROOT_DIR / "ComfyUI_windows_portable"
COMFY_MAIN_PATH = COMFY_PORTABLE_DIR / "ComfyUI" / "main.py"
COMFY_PYTHON_PATH = COMFY_PORTABLE_DIR / "python_embeded" / "python.exe"
COMFY_OUTPUT_DIR = COMFY_PORTABLE_DIR / "ComfyUI" / "output"
