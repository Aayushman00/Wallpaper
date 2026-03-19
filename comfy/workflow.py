"""Workflow loading and mutation helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from config.constants import WORKFLOW_PROMPT_NODE_ID
from core.seed_engine import SeedEngine


class WorkflowManager:
    """Loads and updates the ComfyUI workflow payload."""

    def __init__(self, workflow_path: Path, seed_engine: SeedEngine) -> None:
        self.workflow_path = workflow_path
        self.seed_engine = seed_engine

    def load(self) -> dict[str, Any]:
        """Load the raw workflow JSON."""
        with self.workflow_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def prepare(self, final_prompt: str) -> tuple[dict[str, Any], list[int]]:
        """Inject seeds and prompt text into the workflow."""
        workflow = self.load()
        used_seeds: list[int] = []
        sampler_index = 1

        for node in workflow.values():
            if node.get("class_type") == "KSampler":
                seed = self.seed_engine.get_seed()
                node["inputs"]["seed"] = seed
                logging.info("SEED KSampler %s: %s", sampler_index, seed)
                used_seeds.append(seed)
                sampler_index += 1

        prompt_node = workflow.get(WORKFLOW_PROMPT_NODE_ID)
        if not isinstance(prompt_node, dict) or "inputs" not in prompt_node:
            raise ValueError("Workflow prompt node is missing or invalid")
        prompt_node["inputs"]["text"] = final_prompt
        logging.info("Prompt generated: %s", final_prompt)
        return workflow, used_seeds
