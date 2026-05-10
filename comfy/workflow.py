"""Workflow loading and mutation helpers."""

from __future__ import annotations

import json
import logging
import copy
from pathlib import Path
from typing import Any

from core.seed_engine import SeedEngine


class WorkflowManager:
    """Loads and updates the ComfyUI workflow payload."""

    def __init__(self, workflow_path: Path, seed_engine: SeedEngine) -> None:
        self.workflow_path = workflow_path
        self.seed_engine = seed_engine

    def load(self) -> dict[str, Any]:
        """Load the raw workflow JSON."""
        with self.workflow_path.open("r", encoding="utf-8") as file:
            workflow = json.load(file)

        return copy.deepcopy(workflow)

    def prepare(self, final_prompt: str) -> tuple[dict[str, Any], list[int]]:
        """Inject seeds and prompt text into the workflow."""
        workflow = self.load()
        used_seeds: list[int] = []
        prompt_injected = False
        sampler_index = 1

        for node in workflow.values():
            if node.get("class_type") == "KSampler":
                
                inputs = node.get("inputs", {})

                if "seed" not in inputs:
                    raise RuntimeError("KSampler missing seed inputs")
                
                seed = self.seed_engine.get_seed()
                inputs["seed"] = seed
                logging.info("SEED KSampler %s: %s", sampler_index, seed) 
                used_seeds.append(seed) 
                sampler_index += 1

            if node.get("class_type") == "CLIPTextEncode" and node.get("_meta", {}).get("title") == "Positive":

                inputs = node.get("inputs", {})

                if "text" in inputs:
                    inputs["text"] = final_prompt
                    prompt_injected = True

        if not prompt_injected:
            raise RuntimeError("No positive CLIPTextEncode node found")
        
        if not used_seeds:
            raise RuntimeError("No KSampler node found")
        
        logging.info("Prompt generated: %s", final_prompt)
        
        return workflow, used_seeds
