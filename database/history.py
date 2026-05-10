"""Persistence for wallpaper generation history."""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path


class HistoryRepository:
    """Stores wallpaper generation metadata."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, object]]:
        """Return stored history entries, or an empty list if unavailable."""
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logging.error("Failed to load %s: %s", self.path, exc)
            return []
        except Exception:
            return []
        return []

    def append(
            self, 
            prompt: str, 
            seeds: list[int], 
            score: float, 
            image_path: str, 
            generation_time: float,
            dna: dict[str, object]
        ) -> None:
        """Append a generation record to the history file."""
        records = self.load()
        records.append(
            {
                "prompt": prompt,
                "seeds": seeds,
                "score": score,
                "image_path": image_path,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "generation_time": generation_time,
                "dna": dna
            }
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2)
