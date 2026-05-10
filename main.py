"""Application entry point."""

from __future__ import annotations

import logging
import os
import time

from comfy.client import ComfyClient
from comfy.server import ComfyServer
from comfy.workflow import WorkflowManager
from config.constants import (
    COMFY_BOOT_RETRIES,
    COMFY_BOOT_WAIT_SECONDS,
    GPU_IDLE_RETRIES,
    GPU_IDLE_WAIT_SECONDS,
)
from config.paths import BEST_SEEDS_FILE, HISTORY_FILE, LOG_FILE, WORKFLOW_FILE
from core.prompt_engine import PromptEngine
from core.semantic_scorer import SemanticPromptScorer
from core.aesthetic_scorer import AestheticScorer
from core.seed_engine import SeedEngine
from database.history import HistoryRepository
from database.seeds import SeedRepository
from system.file_manager import FileManager
from system.gpu import GPUMonitor
from system.wallpaper import WallpaperService


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],

        force=True
    )


class WallpaperApplication:
    """Coordinates prompt generation, image rendering, and wallpaper updates."""

    def __init__(self) -> None:
        self.file_manager = FileManager()
        self.seed_engine = SeedEngine(SeedRepository(BEST_SEEDS_FILE))
        self.history_repository = HistoryRepository(HISTORY_FILE)
        self.prompt_engine = PromptEngine()
        self.workflow_manager = WorkflowManager(WORKFLOW_FILE, self.seed_engine)
        self.comfy_server = ComfyServer()
        self.comfy_client = ComfyClient()
        self.gpu_monitor = GPUMonitor()
        self.wallpaper_service = WallpaperService()
        self.semantic_scorer = SemanticPromptScorer()
        self.aesthetic_scorer = AestheticScorer()

    def run(self) -> None:
        """Execute one wallpaper generation cycle."""
        try:
            self.file_manager.ensure_directories()

            logging.info("Script PID: %s", os.getpid())
            logging.info("Wallpaper engine started")

            if not self._wait_for_idle_gpu():
                logging.info("GPU stayed busy, skipping wallpaper generation")
                return

            if not self._ensure_comfy_server():
                logging.error("ComfyUI failed to start")
                return
            
            start_time = time.time()
            result = self._generate_wallpaper()
            if not result:
                logging.info("Wallpaper generation skipped or aborted.")
                return
            
            generation_time = round(time.time() - start_time, 2)
            logging.info("Total generation cycle time: %.2f seconds", generation_time)

            semantic_score = self.semantic_scorer.score(result["path"], result["semantic_prompt"])
            aesthetic_score = self.aesthetic_scorer.score(result["path"])

            combined_score = (
                semantic_score * 0.4
                + aesthetic_score * 6
            )

            logging.info(
                "Combined Score: %.2f",
                combined_score,
            )

            self.history_repository.append(
                seeds=result["seeds"],
                semantic_score=semantic_score,
                aesthetic_score=aesthetic_score,
                combined_score=combined_score,
                image_path=result["path"],
                generation_time=generation_time,
                semantic_prompt=result["semantic_prompt"],
                dna=result["dna"],
            )

            # self.seed_engine.update(
            #     seeds=result["seeds"],
            #     score=score,
            #     prompt=result["prompt"],
            #     tags=result.get("tags", []),
            # )

            wallpaper_start_time = time.time()
            self.wallpaper_service.set_wallpaper(result["path_obj"])

            wallpaper_set_time = time.time() - wallpaper_start_time
            logging.info("Wallpaper set successfully in %.2f seconds", wallpaper_set_time)
        except Exception as exc:
            logging.exception("Wallpaper generation cycle failed: %s", exc)
            raise

    def _wait_for_idle_gpu(self) -> bool:
        for _ in range(GPU_IDLE_RETRIES):
            if self.gpu_monitor.is_idle():
                return True
            logging.info("GPU busy, retrying in 2 minutes")
            time.sleep(GPU_IDLE_WAIT_SECONDS)
        return False

    def _ensure_comfy_server(self) -> bool:
        if self.comfy_server.is_running():
            return True

        logging.info("ComfyUI not running. Starting...")
        self.comfy_server.start()

        for _ in range(COMFY_BOOT_RETRIES):
            if self.comfy_server.is_running():
                logging.info("ComfyUI started successfully")
                return True
            time.sleep(COMFY_BOOT_WAIT_SECONDS)
        return False

    def _generate_wallpaper(self) -> dict[str, object] | None:
        hour = time.localtime().tm_hour
        time_of_day = "morning" if 5 <= hour < 17 else "night"
        prompt_data = self.prompt_engine.generate(
            time_of_day
        )
        prompt = prompt_data["final_prompt"] 
        semantic_prompt = (
            prompt_data["semantic_prompt"]
        )

        dna = prompt_data["dna"]

        workflow, used_seeds = self.workflow_manager.prepare(prompt)
        
        prompt_id = self.comfy_client.queue_prompt(workflow)
        if not prompt_id:
            return None

        image_info = self.comfy_client.wait_for_image(prompt_id)
        if not image_info:
            return None

        destination = self.file_manager.move_generated_image(
            filename=image_info["filename"],
            subfolder=image_info["subfolder"],
        )

        return {
            "path": str(destination),
            "path_obj": destination,
            "prompt": prompt,
            "semantic_prompt": semantic_prompt,
            "seeds": used_seeds,
            "dna": dna,
        }


def main() -> None:
    """Program entry point."""
    setup_logging()
    WallpaperApplication().run()


if __name__ == "__main__":
    main()
