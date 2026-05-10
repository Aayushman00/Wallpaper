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

    def generate(
            self, 
            time_of_day: str,
            trait_scores: dict[str, dict[str, float]],
        ) -> dict[str, object]:

        """Generate a prompt using the weighted behavior."""

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


        atmosphere = ", ".join(
            random.sample(
                ATMOSPHERE,
                2,
            )
        )

        camera = self.weighted_choice(
            "camera",
            CAMERA,
            trait_scores,
        )

        detail = self.weighted_choice(
            "detail",
            DETAIL,
            trait_scores,
        )

        camera_physics = self.weighted_choice(
            "camera_physics",
            CAMERA_PHYSICS,
            trait_scores,
        )

        lighting_options = (
            MORNING_LIGHT
            if time_of_day == "morning"
            else NIGHT_LIGHT
        )

        lighting = self.weighted_choice(
            "lighting",
            lighting_options,
            trait_scores,
        )

        semantic_template = self.weighted_choice(
            "semantic_template",
            SEMANTIC_TEMPLATES,
            trait_scores,
            0.5
        )
        render_template = self.weighted_choice(
            "render_template",
            RENDER_TEMPLATES,
            trait_scores,
            0.5,
        )

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

            "semantic_template": semantic_template,

            "render_template": render_template,
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
    
    def weighted_choice(
            self,
            trait_name: str,
            options: list[str],
            trait_scores: dict[str, dict[str, float]],
            random_prob=0.3,
    ) -> str:
        
        if random.random() < random_prob:
            return random.choice(options)
        
        weights = []

        trait_data = (
            trait_scores.get(
                trait_name,
                {}
            )
        )

        for option in options:

            score = trait_data.get(
                option, 
                1,
            )

            weights.append(score + 1)

        

        return random.choices(
            options,
            weights=weights,
            k=1,
        )[0]
