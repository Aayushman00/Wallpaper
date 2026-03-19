"""Filesystem helpers for generated wallpapers and logging setup."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from config.paths import COMFY_OUTPUT_DIR, DATABASE_DIR, LOGS_DIR, WALLPAPERS_DIR


class FileManager:
    """Handles directory setup and generated image movement."""

    def ensure_directories(self) -> None:
        """Create required runtime directories."""
        for path in (WALLPAPERS_DIR, LOGS_DIR, DATABASE_DIR):
            path.mkdir(parents=True, exist_ok=True)

    def move_generated_image(self, filename: str, subfolder: str) -> Path:
        """Move an image from the ComfyUI output folder into the wallpapers folder."""
        source = COMFY_OUTPUT_DIR / subfolder / filename
        if not source.exists():
            logging.error("Generated image not found: %s", source)
            raise FileNotFoundError(source)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        destination = WALLPAPERS_DIR / f"{timestamp}.png"
        shutil.move(str(source), str(destination))
        logging.info("Wallpaper generated successfully: %s", destination)
        return destination
