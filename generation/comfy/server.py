"""ComfyUI server lifecycle helpers."""

from __future__ import annotations

import logging
import subprocess

import requests

from config.settings import COMFY_URL
from config.paths import COMFY_MAIN_PATH, COMFY_PORTABLE_DIR, COMFY_PYTHON_PATH, COMFY_USER_DIR


class ComfyServer:
    """Checks and starts the local ComfyUI server."""

    def is_running(self) -> bool:
        """Return True when the ComfyUI API responds."""
        try:
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=2)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def start(self) -> None:
        """Start the ComfyUI server as a detached process."""
        logging.info("Starting ComfyUI server...")
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        try: 
            process = subprocess.Popen(
                [
                    str(COMFY_PYTHON_PATH),
                    "-s",
                    str(COMFY_MAIN_PATH),
                    "--windows-standalone-build",
                    "--base-directory",
                    str(COMFY_USER_DIR),
                ],
                cwd=str(COMFY_PORTABLE_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            logging.info("ComfyUI started with PID %s", process.pid)
        except OSError as exc:
            logging.error("Failed to launch ComfyUI: %s", exc)
            raise
