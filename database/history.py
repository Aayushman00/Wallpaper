"""Persistence for wallpaper generation history."""

from __future__ import annotations

import json
import os
import threading
import time
import logging
from pathlib import Path


class HistoryRepository:
    """Stores wallpaper generation metadata.

    Shared between the scheduler thread (append) and the hotkey thread
    (set_rating, revert's load), so every public method takes one lock.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def load(self) -> list[dict[str, object]]:
        """Return stored history entries, or an empty list if unavailable."""
        with self._lock:
            return self._read()

    def _read(self) -> list[dict[str, object]]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise RuntimeError(
                    f"History file must contain a list: {self.path}"
                )
            return data

        except FileNotFoundError:
            return []

        except json.JSONDecodeError as exc:
            logging.error("Failed to load %s: %s", self.path, exc)
            corrupt_path = self.path.with_suffix(".corrupt")

            self.path.replace(corrupt_path)

            raise RuntimeError(
                f"Corrupt JSON file: {self.path}"
            ) from exc

        except Exception as exc:
            raise RuntimeError(
                f"Unexpected history load failure: {self.path}"
            ) from exc

    def _write(self, records: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")

        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2)
            file.flush()
            os.fsync(file.fileno())

        tmp_path.replace(self.path)

    def append(
            self,
            seeds: list[int],
            semantic_score: float,
            aesthetic_score: float,
            combined_score: float,
            image_path: str,
            generation_time: float,
            semantic_prompt: str,
            dna: dict[str, object],
            quarantined: bool = False,
        ) -> None:
        """Append a generation record to the history file."""
        with self._lock:
            records = self._read()
            records.append(
                {
                    "seeds": seeds,
                    "semantic_score": semantic_score,
                    "aesthetic_score": aesthetic_score,
                    "combined_score": combined_score,
                    "image_path": image_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "generation_time": generation_time,
                    "semantic_prompt": semantic_prompt,
                    "dna": dna,
                }
            )

            if quarantined:
                records[-1]["quarantined"] = True

            self._write(records)

    def set_rating(self, image_path: str, rating: int) -> bool:
        """Set `rating` (+1 liked / -1 disliked) on the newest entry for `image_path`.

        Idempotent: a later rating replaces an earlier one. Returns False, writing
        nothing, if no entry has that image_path. Raises ValueError, before any I/O,
        unless rating is exactly the int 1 or -1 (bool, float, str, None are rejected).
        """
        if type(rating) is not int or rating not in (1, -1):
            raise ValueError(f"rating must be +1 or -1, got {rating!r}")

        with self._lock:
            records = self._read()
            for record in reversed(records):
                if record.get("image_path") == image_path:
                    record["rating"] = rating
                    self._write(records)
                    return True
            return False
