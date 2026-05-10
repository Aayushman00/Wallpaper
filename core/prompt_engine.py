"""Prompt generation logic."""

from __future__ import annotations

import logging
import random

from config.constants import (
    ATMOSPHERE,
    CAMERA,
    CAMERA_PHYSICS,
    DETAIL,
    MORNING_LIGHT,
    NIGHT_LIGHT,
    PROMPT_DICT,
    SEMANTIC_TEMPLATES,
    RENDER_TEMPLATES,
)


class PromptEngine:
    """Builds prompts from themed prompt fragments."""

    def generate(self, time_of_day: str) -> str:
        """Generate a prompt using the original weighted random behavior."""
        theme = random.choice(list(PROMPT_DICT.keys()))
        logging.info("THEME: %s", theme)
        data = PROMPT_DICT[theme]

        subject = random.choice(data["subject"])
        location_data = random.choice(
            data["location"]
        )
        location_preposition = (
            location_data["preposition"]
        )
        location = location_data["value"]

        location_phrase = " ".join(
            filter(
                None,
                [
                    location_preposition,
                    location,
                ],
            )
        )

        environment = ", ".join(random.sample(data["environment"], 2))
        atmosphere = ", ".join(random.sample(ATMOSPHERE, 2))
        camera = random.choice(CAMERA)
        detail = random.choice(DETAIL)
        camera_physics = random.choice(CAMERA_PHYSICS)
        lighting = random.choice(MORNING_LIGHT if time_of_day == "morning" else NIGHT_LIGHT)
        semantic_template = random.choice(SEMANTIC_TEMPLATES)
        render_template = random.choice(RENDER_TEMPLATES)

        dna = {
            "theme": theme,

            "subject": subject,

            "location_phrase": location_phrase,

            "environment": environment,

            "lighting": lighting,

            "atmosphere": atmosphere,

            "camera": camera,

            "camera_physics": camera_physics,

            "detail": detail,
        }

        semantic_prompt = semantic_template.format(
            **dna
        )

        render_prompt = render_template.format(
            **dna
        )

        final_prompt = (
            semantic_prompt
            + ", "
            + render_prompt
        )

        return {
            "semantic_prompt": semantic_prompt,
            "render_prompt": render_prompt,
            "final_prompt": final_prompt,
            "dna": dna,
        }
