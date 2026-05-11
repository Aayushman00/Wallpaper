"""Prompt generation logic."""

from __future__ import annotations

import logging
import random

from config.constants_v2 import (
    THEMES,
    LIGHT_QUALITY,
    MOOD,
    LIGHTING_TIME,
    FRAMING_TYPE,
    LENS_CHARACTER,
    RENDER_MEDIUM,
    RENDER_QUALITY_MARKERS,
    RENDER_TEMPLATES,
    SEMANTIC_TEMPLATES_BY_TYPE,
    is_lighting_compatible, 
    is_lens_framing_compatible,
    get_environmental_condition,
)

class PromptEngineV2: 


    def pick_weighted(
            self, 
            items: list[dict], 
            key="weight",
        ) -> dict:


        if not items:
            raise RuntimeError(
                "Attempted weighted selection from empty list."
            )
        weights = [i[key] for i in items]
        return random.choices(items, weights=weights, k=1)[0]

    def generate(
            self, 

        ) -> dict[str, object]:

        theme_name = random.choice(
            list(THEMES.keys())
        )


        logging.info(
            "V2 THEME: %s",
            theme_name,
        )


        theme_data = THEMES[theme_name]

        # 1. Subject — typed
        subject = random.choices(
            theme_data["subjects"],
            weights=theme_data["subject_weights"],
            k=1
        )[0]
        subject_type = subject["type"]

        # 2. Location — filtered by subject type
        valid_locations = [
            loc for loc in theme_data["locations"]
            if subject_type in loc["valid_for"]
        ]
        location = random.choice(valid_locations)

        # 3. Environment — purely descriptive of surroundings
        environment = self.pick_weighted(theme_data["environments"])

        # 4. Lighting

        if theme_name == "space":
            time_pool = LIGHTING_TIME["space_only"]
        else:
            time_pool = LIGHTING_TIME["universal"]

        light_time = self.pick_weighted(
            time_pool
        )

        valid_light_qualities = [

            quality
            for quality in LIGHT_QUALITY

            if is_lighting_compatible(
                light_time["label"],
                quality["label"],
            )
        ]

        light_quality = self.pick_weighted(
            valid_light_qualities
        )

        # 5. Mood
        mood = self.pick_weighted(MOOD)

        # 6. Composition

        valid_framings = [
            f for f in FRAMING_TYPE
            if subject_type in f["valid_for"]
        ]

        framing = self.pick_weighted(
            valid_framings
        )

        valid_lenses = [

            lens
            for lens in LENS_CHARACTER

            if is_lens_framing_compatible(
                lens["label"],
                framing["label"],
            )
        ]

        lens = self.pick_weighted(
            valid_lenses
        )

        valid_render_mediums = [

            render
            for render in RENDER_MEDIUM

            if subject_type not in render.get(
                "incompatible_subject_types",
                [],
            )

            and theme_name not in render.get(
                "incompatible_themes",
                [],
            )
        ]

        render_medium = self.pick_weighted(
            valid_render_mediums
        )

        valid_quality_markers = [

            marker
            for marker in RENDER_QUALITY_MARKERS

            if any(
                material in marker["valid_for"]
                for material in subject["material_class"]
            )

            and render_medium["label"] not in marker.get(
                "incompatible_render",
                [],
            )
        ]

        quality_marker = self.pick_weighted(
            valid_quality_markers
        )


        # 8. Semantic template — typed to subject
        templates = SEMANTIC_TEMPLATES_BY_TYPE[subject_type]
        semantic_template = self.pick_weighted(
                                templates
                            )
        

        environmental_condition_pool = (
            get_environmental_condition(
                theme_name
            )
        )

        environmental_condition = (
            self.pick_weighted(
                environmental_condition_pool
            )
        )


        # 9. Render template
        render_template = self.pick_weighted(
            RENDER_TEMPLATES
        )

        # Assemble
        template_string = semantic_template[
            "template"
        ]

        template_data = {
            "subject": subject["label"],
            "location": location["label"],
            "environment": environment["label"],
        }

        if semantic_template["uses_condition"]:

            template_data["condition"] = (
                environmental_condition["label"]
            )

        semantic = template_string.format(
            **template_data
        )

        render = render_template["template"].format(
            render_medium=render_medium["label"],
            lens=lens["label"],
            quality_marker=quality_marker["label"],
        )

        dna = {
            "theme": theme_name,

            "subject": subject["label"],

            "subject_type": subject_type,

            "location": location["label"],

            "environment": environment["label"],

            "mood": mood["label"],

            "light_time": light_time["label"],

            "light_quality": light_quality["label"],

            "framing": framing["label"],

            "lens": lens["label"],

            "render_medium": render_medium["label"],

            "quality_marker": quality_marker["label"],

            "environmental_condition": (
                environmental_condition["label"]
            ),
        }

        # Final prompt: semantic + mood + lighting + render
        # Mood and lighting sit between semantic and render — they bridge content and style
        prompt = (
            f"{semantic}, "
            f"{mood['label']} mood, "
            f"{light_time['label']}, {light_quality['label']} light, "
            f"{framing['label']}, "
            f"{render}"
        )

        return {
            "semantic_prompt": semantic,
            "render_prompt": render,
            "final_prompt": prompt,
            "dna": dna,
        }


