"""Workflow loading and mutation helpers."""

from __future__ import annotations

import json
import logging
import copy
from pathlib import Path
from typing import Any

from core.seed_engine import SeedEngine
from config.settings import (
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_IMAGE_SHARPEN_NODE_ID,
    WORKFLOW_LATENT_UPSCALE_NODE_ID,
    WORKFLOW_KSAMPLER_FIRST_NODE_ID,
    WORKFLOW_KSAMPLER_SECOND_NODE_ID
)


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
    
    def _clamp(
        self,
        value: float,
        minimum: float,
        maximum: float
    ) -> float:

        return max(minimum, min(value, maximum))
    
    def _build_profile(
            self,
            theme: str,
            density: int,
            subject_type: str,
            mood: str,
    ) -> dict[str, Any]:
        
        profile = {
            "profile_name": "default",

            "first_cfg": 5.8,
            "first_steps": 32,
            "first_sampler": "dpmpp_2m_sde_gpu",

            "second_cfg": 3.8,
            "second_steps": 18,
            "second_sampler": "dpmpp_3m_sde_gpu",
            "second_denoise": 0.45,

            "latent_scale": 1.5,

            "sharpen_alpha": 0.12,
        }


        if theme == "fantasy":

            profile.update({
                "profile_name": "fantasy",

                "first_cfg": 6.0,
                "second_cfg": 4.5,

                "second_denoise": 0.52,

            })

        elif theme == "cyberpunk":

            profile.update({
                "profile_name": "cyberpunk",

                "first_cfg": 5.4,
                "second_cfg": 4.0,

                "latent_scale": 1.32,

                "sharpen_alpha": 0.10,

            })
        
        elif theme == "space":

            profile.update({
                "profile_name": "space",

                "first_cfg": 5.2,
                "second_cfg": 4.2,

                "latent_scale": 1.42,

                "sharpen_alpha": 0.09,
            })
        
        if density >= 8:

            profile["first_cfg"] -= 0.5
            profile["first_steps"] += 4
            profile["sharpen_alpha"] -= 0.03

        elif density <= 3:

            profile["second_denoise"] += 0.05
            profile["latent_scale"] += 0.1

        profile["second_denoise"] = self._clamp(profile["second_denoise"], 0.44, 0.6)

        logging.info(
            "PROFILE SETTINGS | cfg1 = %s cfg2 = %s denoise = %s scale = %s",
            profile["first_cfg"],
            profile["second_cfg"],
            profile["second_denoise"],
            profile["latent_scale"],
        )

        return profile

    def prepare(
        self,
        final_prompt: str,
        dna: dict[str, object]
    ) -> tuple[dict[str, Any], list[int]]:

        workflow = self.load()

        used_seeds: list[int] = []
        prompt_injected = False
        sampler_index = 1

        theme = str(dna.get("theme", "generic"))
        density = int(dna.get("scene_density_score", 5))
        subject_type = str(dna.get("subject_type", "structure"))
        mood = str(dna.get("mood", ""))

        profile = self._build_profile(
            theme=theme,
            density=density,
            subject_type=subject_type,
            mood=mood
        )

        for node_id, node in workflow.items():

            class_type = node.get("class_type")
            inputs = node.get("inputs", {})

            if class_type == "KSampler":

                if "seed" not in inputs:
                    raise RuntimeError("KSampler missing seed input")

                seed = self.seed_engine.get_seed()

                inputs["seed"] = seed

                used_seeds.append(seed)

                logging.info(
                    "SEED KSampler %s: %s",
                    sampler_index,
                    seed
                )

                if node_id == WORKFLOW_KSAMPLER_FIRST_NODE_ID:

                    inputs["cfg"] = profile["first_cfg"]
                    inputs["steps"] = profile["first_steps"]
                    inputs["sampler_name"] = profile["first_sampler"]

                elif node_id == WORKFLOW_KSAMPLER_SECOND_NODE_ID:

                    inputs["cfg"] = profile["second_cfg"]
                    inputs["steps"] = profile["second_steps"]
                    inputs["denoise"] = profile["second_denoise"]
                    inputs["sampler_name"] = profile["second_sampler"]

                sampler_index += 1

            elif (
                class_type == "CLIPTextEncode"
                and node_id == WORKFLOW_PROMPT_NODE_ID
            ):

                if "text" in inputs:

                    inputs["text"] = final_prompt
                    prompt_injected = True

            elif (
                class_type == "LatentUpscaleBy"
                and node_id == WORKFLOW_LATENT_UPSCALE_NODE_ID
            ):

                inputs["scale_by"] = profile["latent_scale"]

            elif (
                class_type == "ImageSharpen"
                and node_id == WORKFLOW_IMAGE_SHARPEN_NODE_ID    
            ):

                inputs["alpha"] = profile["sharpen_alpha"]

        if not prompt_injected:
            raise RuntimeError("No positive CLIPTextEncode node found")

        if not used_seeds:
            raise RuntimeError("No KSampler node found")

        logging.info("Prompt generated: %s", final_prompt)

        logging.info(
            "Workflow profile applied: %s",
            profile["profile_name"]
        )

        return workflow, used_seeds
