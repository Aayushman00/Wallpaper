"""One wallpaper-generation cycle: GPU-idle wait, generate, evaluate, persist, apply."""

from __future__ import annotations

import logging
import time

from config.settings import AESTHETIC_QUALITY_FLOOR, GPU_IDLE_RETRIES, GPU_IDLE_WAIT_SECONDS
from engine.models import CycleResult, GenerationRequest


class WallpaperEngine:
    """Coordinates prompt generation, image rendering, and wallpaper updates."""

    def __init__(
        self,
        backend,
        prompt_engine,
        seed_pool,
        history_repository,
        wallpaper_service,
        gpu_monitor,
        semantic_scorer_factory,
        aesthetic_scorer_factory,
        sleep=time.sleep,
    ) -> None:
        self.backend = backend
        self.prompt_engine = prompt_engine
        self.seed_pool = seed_pool
        self.history_repository = history_repository
        self.wallpaper_service = wallpaper_service
        self.gpu_monitor = gpu_monitor
        self._semantic_scorer_factory = semantic_scorer_factory
        self._aesthetic_scorer_factory = aesthetic_scorer_factory
        self._sleep = sleep
        self._semantic_scorer = None
        self._aesthetic_scorer = None

    def _get_semantic_scorer(self):
        if self._semantic_scorer is None:
            self._semantic_scorer = self._semantic_scorer_factory()
        return self._semantic_scorer

    def _get_aesthetic_scorer(self):
        if self._aesthetic_scorer is None:
            self._aesthetic_scorer = self._aesthetic_scorer_factory()
        return self._aesthetic_scorer

    def run(self, context: dict | None = None) -> CycleResult | None:
        """Execute one wallpaper generation cycle."""
        try:
            if not self._wait_for_idle_gpu():
                logging.info("GPU stayed busy, skipping wallpaper generation")
                return

            if not self.backend.ensure_ready():
                logging.error("ComfyUI failed to start")
                return

            if context:
                prompt_data = self.prompt_engine.generate(context=context)
            else:
                prompt_data = self.prompt_engine.generate()
            request = GenerationRequest(
                prompt=prompt_data["final_prompt"],
                dna=prompt_data["dna"],
            )

            result = self.backend.generate(request)
            if not result:
                logging.info("Wallpaper generation skipped or aborted.")
                return

            logging.info("Total generation cycle time: %.2f seconds", result.generation_time_seconds)

            semantic_score = self._get_semantic_scorer().score(
                str(result.image_path), prompt_data["semantic_prompt"]
            )
            aesthetic_score = self._get_aesthetic_scorer().score(str(result.image_path))

            semantic_norm = semantic_score / 100
            aesthetic_norm = aesthetic_score / 10
            combined_score = semantic_norm * 0.4 + aesthetic_norm * 0.6

            logging.info("Combined Score: %.2f", combined_score)

            quarantined = aesthetic_score < AESTHETIC_QUALITY_FLOOR
            generation = max((g for _, g in result.used_lineage), default=0)

            self.history_repository.append(
                seeds=result.used_seeds,
                semantic_score=semantic_score,
                aesthetic_score=aesthetic_score,
                combined_score=combined_score,
                image_path=str(result.image_path),
                generation_time=result.generation_time_seconds,
                semantic_prompt=prompt_data["semantic_prompt"],
                dna=prompt_data["dna"],
                quarantined=quarantined,
            )

            if quarantined:
                logging.warning(
                    "Aesthetic score %.2f below floor %.2f, quarantining image",
                    aesthetic_score, AESTHETIC_QUALITY_FLOOR,
                )
                self.seed_pool.penalize(result.used_seeds)
                return CycleResult(result.image_path, result.used_seeds, generation, quarantined=True)

            self.seed_pool.record_result(
                seeds=result.used_seeds,
                score=combined_score,
                prompt=request.prompt,
                theme=prompt_data["dna"]["theme"],
                lineage=result.used_lineage,
            )

            self.wallpaper_service.set_wallpaper(result.image_path)
            return CycleResult(result.image_path, result.used_seeds, generation)
        except Exception as exc:
            logging.exception("Wallpaper generation cycle failed: %s", exc)
            raise

    def _wait_for_idle_gpu(self) -> bool:
        for _ in range(GPU_IDLE_RETRIES):
            if self.gpu_monitor.is_idle():
                return True
            logging.info("GPU busy, retrying in 2 minutes")
            self._sleep(GPU_IDLE_WAIT_SECONDS)
        return False
