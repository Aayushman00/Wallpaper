"""ComfyUI generation backend — the only file that translates domain
GenerationRequest/GenerationResult to and from ComfyUI's workflow JSON
and HTTP API."""

from __future__ import annotations

import logging
import time

from config.settings import COMFY_BOOT_RETRIES, COMFY_BOOT_WAIT_SECONDS
from engine.models import GenerationRequest, GenerationResult


class ComfyBackend:
    """Generation backend adapter for a local ComfyUI instance."""

    def __init__(self, client, server, workflow, file_manager, sleep=time.sleep) -> None:
        self.client = client
        self.server = server
        self.workflow = workflow
        self.file_manager = file_manager
        self._sleep = sleep

    def ensure_ready(self) -> bool:
        """Start the ComfyUI process if it isn't running, and wait for it to boot."""
        if self.server.is_running():
            return True

        logging.info("ComfyUI not running. Starting...")
        self.server.start()

        for _ in range(COMFY_BOOT_RETRIES):
            if self.server.is_running():
                logging.info("ComfyUI started successfully")
                return True
            self._sleep(COMFY_BOOT_WAIT_SECONDS)
        return False

    def generate(self, request: GenerationRequest) -> GenerationResult | None:
        """Submit a generation request to ComfyUI and return the result, or None on failure."""
        start_time = time.time()

        workflow, used_seeds, used_lineage = self.workflow.prepare(request.prompt, request.dna)

        prompt_id = self.client.queue_prompt(workflow)
        if not prompt_id:
            return None

        image_info = self.client.wait_for_image(prompt_id)
        if not image_info:
            return None

        destination = self.file_manager.move_generated_image(
            filename=image_info["filename"],
            subfolder=image_info["subfolder"],
        )

        return GenerationResult(
            image_path=destination,
            used_seeds=used_seeds,
            used_lineage=used_lineage,
            generation_time_seconds=round(time.time() - start_time, 2),
        )
