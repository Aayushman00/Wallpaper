"""Persistence for evolved seed history."""

from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from typing import Any

class SeedRepository:
    """Stores and retrieves seed performance data."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        """Return stored seed records, or an empty list if unavailable."""
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
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
        
        except Exception:
            raise RuntimeError(
                f"Corrupt JSON file: {self.path}"
            ) from exc
        
        return []

    def save(self, records: list[dict[str, Any]]) -> None:
        """Persist seed records to disk."""
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
