"""Persistence for wallpaper generation history."""

from __future__ import annotations

import json
import os
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
        
        return []

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
        records = self.load()
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

        self.path.parent.mkdir(parents=True, exist_ok=True)


        tmp_path = self.path.with_suffix(".tmp")

        with tmp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                records, 
                file, 
                indent=2,
            )

            file.flush()

            os.fsync(file.fileno()) 

        tmp_path.replace(self.path)
