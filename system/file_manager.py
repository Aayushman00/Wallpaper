"""Filesystem helpers for generated wallpapers and logging setup."""

from __future__ import annotations

import logging
import shutil
from PIL import Image
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
        try: 
            with Image.open(source) as img:
                img.verify()

            with Image.open(source) as img:
                width, height = img.size
                image_format = img.format
                image_mode = img.mode
        
        except Exception as e:
            logging.error("Generated image is corrupted: %s", e)
            raise
        
        if width <= 0 or height <= 0:
            raise RuntimeError("Invalid generated image dimensions")

        logging.info(
            "Generated Image resolution: %sx%s", 
            width, height,
        )

        aspect_ratio = round(width / height, 2)

        logging.info("Aspect ratio: %.2f", 
                     aspect_ratio,
        )

        logging.info(
            "Image format: %s | Mode: %s",
            image_format,
            image_mode,
        )

        size_mb = source.stat().st_size / (1024 * 1024)
        if source.stat().st_size == 0:
            raise RuntimeError("Generated Image file is empty")
        logging.info("Generated image size: %.2f MB", size_mb)


        timestamp = time.strftime("%Y%m%d_%H%M%S")
        milliseconds = int((time.time() % 1) * 1000)
        move_start = time.time()
        destination = WALLPAPERS_DIR / f"{timestamp}_{milliseconds}.png"
        logging.info(
            "Moving generated image from %s to %s",
            source, 
            destination,
        )
        max_attempts = 10

        for attempt in range(max_attempts):
            try:
                shutil.move(str(source), str(destination))
                break

            except PermissionError:
                logging.warning(
                    "File still locked, retrying move (%s/%s)",
                    attempt + 1,
                    max_attempts,
                )
                time.sleep(0.5)

        else:
            raise PermissionError(
                f"Could not move generated image after {max_attempts} attempts"
            )
        logging.info("Image move completed in %0.2f seconds", time.time() - move_start)

        logging.info("Generated filename: %s", destination.name)
        return destination
