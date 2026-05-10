"""Filesystem paths used by the application."""

from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_FILE = ROOT_DIR / "wallpaper.json"
LOGS_DIR = ROOT_DIR / "logs"
WALLPAPERS_DIR = ROOT_DIR / "wallpapers"
DATABASE_DIR = ROOT_DIR / "database"
LOG_FILE = LOGS_DIR / "wallpaper_engine.log"
DATA_DIR = ROOT_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
BEST_SEEDS_FILE = DATA_DIR / "best_seeds.json"

COMFY_RESOURCES_DIR = Path(
    os.getenv(
        "COMFY_RESOURCES_DIR",
        str(Path.home() / "AppData/Local/Programs/ComfyUI/resources"),
    )
)

COMFY_USER_DIR = Path(
    os.getenv(
        "COMFY_USER_DIR",
        str(Path.home() / "Documents/ComfyUI"),
    )
)

COMFY_PORTABLE_DIR = COMFY_RESOURCES_DIR / "ComfyUI"
COMFY_MAIN_PATH = COMFY_PORTABLE_DIR / "main.py"
COMFY_PYTHON_PATH = COMFY_USER_DIR / ".venv" / "Scripts" / "python.exe"
COMFY_OUTPUT_DIR = COMFY_USER_DIR / "output"
