"""HTTP client for ComfyUI prompt execution."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from config.constants import COMFY_URL, GENERATION_TIMEOUT_SECONDS, HISTORY_POLL_SECONDS


class ComfyClient:
    """Submits workflows to ComfyUI and waits for results."""

    def __init__(self, base_url: str = COMFY_URL) -> None:
        self.base_url = base_url

    def queue_prompt(self, workflow: dict[str, Any]) -> str | None:
        """Submit a workflow and return the prompt id."""
        try:
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()["prompt_id"]
        except Exception as exc:
            logging.error("Failed to send workflow to ComfyUI: %s", exc)
            return None

    def wait_for_image(self, prompt_id: str, timeout: int = GENERATION_TIMEOUT_SECONDS) -> dict[str, str] | None:
        """Poll ComfyUI history until an image is available or the timeout expires."""
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                logging.warning("Generation timeout reached.")
                return None

            try:
                response = requests.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=10,
                )
                response.raise_for_status()
                history = response.json()
            except requests.exceptions.HTTPError as e:
                logging.warning(f"ComfyUI history request failed: {e}")
            except Exception:
                logging.warning("ComfyUI history request timed out, retrying...")
                time.sleep(HISTORY_POLL_SECONDS)
                continue

            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node in outputs.values():
                    images = node.get("images", [])
                    if images:
                        image = images[0]
                        return {
                            "filename": image["filename"],
                            "subfolder": image["subfolder"],
                        }

            time.sleep(HISTORY_POLL_SECONDS)
