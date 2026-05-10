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
        location = random.choice(data["location"])
        environment = ", ".join(random.sample(data["environment"], 2))
        atmosphere = ", ".join(random.sample(ATMOSPHERE, 2))
        camera = random.choice(CAMERA)
        detail = random.choice(DETAIL)
        camera_physics = random.choice(CAMERA_PHYSICS)
        lighting = random.choice(MORNING_LIGHT if time_of_day == "morning" else NIGHT_LIGHT)
        semantic_template = random.choice(SEMANTIC_TEMPLATES)
        render_template = random.choice(RENDER_TEMPLATES)

        return (
            semantic_template.format(
                subject=subject,
                location=location,
                environment=environment,
                lighting=lighting,
            ) + render_template.format(
                atmosphere = atmosphere,
                detail = detail,
                camera=camera,
                camera_physics=camera_physics,
            )
        )
