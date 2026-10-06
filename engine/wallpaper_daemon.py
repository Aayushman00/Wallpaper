"""Resident daemon: scheduled generation on one thread, global hotkeys on another."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from config.settings import FOCUS_ASSIST_RECHECK_SECONDS, GENERATION_INTERVAL_SECONDS
from generation.context_signals import get_context as default_get_context
from system.hotkeys import (
    MOD_ALT, MOD_CONTROL, VK_DOWN, VK_LEFT, VK_RIGHT, VK_UP, HotkeyListener,
)


class WallpaperDaemon:
    """Wraps WallpaperEngine.run() in a timer loop and exposes hotkey actions."""

    def __init__(
        self,
        engine,
        seed_pool,
        history_repository,
        wallpaper_service,
        state_path: Path,
        is_fullscreen,
        get_context=default_get_context,
        interval: float = GENERATION_INTERVAL_SECONDS,
        recheck: float = FOCUS_ASSIST_RECHECK_SECONDS,
        listener_factory=HotkeyListener,
    ) -> None:
        self.engine = engine
        self.seed_pool = seed_pool
        self.history_repository = history_repository
        self.wallpaper_service = wallpaper_service
        self.state_path = state_path
        self.is_fullscreen = is_fullscreen
        self.get_context = get_context
        self.interval = interval
        self.recheck = recheck
        self._listener_factory = listener_factory

        self._wake = threading.Event()   # set by generate_next() or stop()
        self._stop = threading.Event()
        self._scheduler: threading.Thread | None = None
        self._hotkey_thread: threading.Thread | None = None
        self._listener = None
        self.state: dict | None = self._load_state()

    # --- state -----------------------------------------------------------

    def _load_state(self) -> dict | None:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            logging.error("Ignoring unreadable %s: %s", self.state_path, exc)
            return None

    def _save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        tmp_path.replace(self.state_path)
        self.state = state

    # --- one cycle -------------------------------------------------------

    def run_cycle(self) -> None:
        """Run one generation; never raises — a resident process outlives bad cycles."""
        try:
            result = self.engine.run(context=self.get_context())
            if result is None or result.quarantined:
                return
            self._save_state({
                "seeds": result.used_seeds,
                "image_path": str(result.image_path),
                "generation": result.generation,
            })
        except Exception:
            logging.exception("Generation cycle failed, will retry on the next schedule")

    # --- hotkey actions --------------------------------------------------

    def like(self) -> None:
        self._rate(liked=True)

    def dislike(self) -> None:
        self._rate(liked=False)

    def _rate(self, liked: bool) -> None:
        state = self.state
        if not state:
            logging.info("No current wallpaper to rate")
            return
        if self.seed_pool.rate_current(state["seeds"], liked=liked):
            logging.info("Rated current wallpaper %s", "up" if liked else "down")
        else:
            logging.info("Current wallpaper's seeds are not in the seed pool, rating had no effect")

    def generate_next(self) -> None:
        self._wake.set()

    def revert(self) -> None:
        entries = [e for e in self.history_repository.load() if not e.get("quarantined", False)]
        if len(entries) < 2:
            logging.info("No previous wallpaper to revert to")
            return
        previous = Path(entries[-2]["image_path"])
        if not previous.exists():
            logging.warning("Previous wallpaper missing on disk: %s", previous)
            return
        self.wallpaper_service.set_wallpaper(previous)
        # Rating means "rate what I see": point current state at the reverted-to image.
        self._save_state({
            "seeds": entries[-2].get("seeds", []),
            "image_path": str(previous),
            "generation": entries[-2].get("generation", 0),
        })

    def _hotkey_bindings(self) -> list[tuple[int, int, object]]:
        ctrl_alt = MOD_CONTROL | MOD_ALT
        return [
            (ctrl_alt, VK_UP, self.like),
            (ctrl_alt, VK_DOWN, self.dislike),
            (ctrl_alt, VK_RIGHT, self.generate_next),
            (ctrl_alt, VK_LEFT, self.revert),
        ]

    # --- threads ---------------------------------------------------------

    def _scheduler_loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(self.interval)
            while not self._stop.is_set() and not self._wake.is_set() and self.is_fullscreen():
                logging.info("Fullscreen app active, deferring generation")
                self._wake.wait(self.recheck)
            if self._stop.is_set():
                break
            self._wake.clear()
            self.run_cycle()

    def start(self) -> None:
        self._scheduler = threading.Thread(target=self._scheduler_loop, name="scheduler", daemon=True)
        self._listener = self._listener_factory(self._hotkey_bindings())
        self._hotkey_thread = threading.Thread(target=self._listener.run, name="hotkeys", daemon=True)
        self._scheduler.start()
        self._hotkey_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._listener is not None:
            self._listener.stop()
        if self._scheduler is not None:
            self._scheduler.join(timeout=5)

    def run_forever(self) -> None:
        self.start()
        try:
            while self._scheduler.is_alive():
                self._scheduler.join(timeout=0.5)
        except KeyboardInterrupt:
            logging.info("Interrupted, shutting down")
        finally:
            self.stop()
