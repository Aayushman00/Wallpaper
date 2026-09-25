"""Application entry point."""

from __future__ import annotations

import logging
import os

from config.paths import BEST_SEEDS_FILE, HISTORY_FILE, LOG_FILE, WORKFLOW_FILE
from database.history import HistoryRepository
from database.seeds import SeedRepository
from engine.seed_pool import SeedPool
from engine.wallpaper_engine import WallpaperEngine
from generation.comfy.backend import ComfyBackend
from generation.comfy.client import ComfyClient
from generation.comfy.server import ComfyServer
from generation.comfy.workflow import WorkflowManager
from generation.prompt_engine import PromptEngine
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
        force=True,
    )


def _semantic_scorer_factory():
    from evaluation.semantic_scorer import SemanticPromptScorer
    return SemanticPromptScorer()


def _aesthetic_scorer_factory():
    from evaluation.aesthetic_scorer import AestheticScorer
    return AestheticScorer()


def build_engine() -> WallpaperEngine:
    """Wire all dependencies and return a ready-to-run WallpaperEngine."""
    file_manager = FileManager()
    file_manager.ensure_directories()

    seed_pool = SeedPool(SeedRepository(BEST_SEEDS_FILE))
    prompt_engine = PromptEngine()

    workflow_manager = WorkflowManager(WORKFLOW_FILE, seed_pool)
    backend = ComfyBackend(
        client=ComfyClient(),
        server=ComfyServer(),
        workflow=workflow_manager,
        file_manager=file_manager,
    )

    return WallpaperEngine(
        backend=backend,
        prompt_engine=prompt_engine,
        seed_pool=seed_pool,
        history_repository=HistoryRepository(HISTORY_FILE),
        wallpaper_service=WallpaperService(),
        gpu_monitor=GPUMonitor(),
        semantic_scorer_factory=_semantic_scorer_factory,
        aesthetic_scorer_factory=_aesthetic_scorer_factory,
    )


def main() -> None:
    """Program entry point."""
    setup_logging()
    logging.info("Script PID: %s", os.getpid())
    logging.info("Wallpaper engine started")
    build_engine().run()


if __name__ == "__main__":
    main()
