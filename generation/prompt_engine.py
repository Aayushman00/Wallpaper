# prompt_engine_v2.py
"""Prompt generation logic — v2.3 SDXL-optimized language layer"""

from __future__ import annotations

import logging
import random
import re
from collections import Counter

from config.prompt_grammar import (
    THEMES,
    LIGHT_QUALITY,
    MOOD_SEMANTICS,
    LIGHTING_TIME,
    FRAMING_TYPE,
    LENS_CHARACTER,
    RENDER_MEDIUM,
    RENDER_QUALITY_MARKERS,
    RENDER_TEMPLATES,
    SCENE_SUFFIX,
    SEMANTIC_TEMPLATES_BY_TYPE,
    CAMERA_ANGLE,
    MAX_SCENE_DENSITY,
    TraitPairMemory,
    DiversityTracker,
    is_lighting_compatible,
    is_lens_framing_compatible,
    is_camera_angle_framing_compatible,
    get_environmental_condition,
    get_mood_list,
    apply_mood_theme_weight,
    apply_mood_condition_weight,
    apply_render_stability,
    get_camera_angle_affinity_boost,
    score_scene_density,
)


class PromptEngine:
    """
    Cinematic procedural prompt engine — v2.3 SDXL-optimized.

    Architecture unchanged from v2.3.
    Language layer refactored for JuggernautXL / SDXL latent alignment:

      - Abstract prose → visual descriptor chunk grammar
      - Mood fields → visually grounded scene descriptors
      - Camera/lens labels → SDXL-native photographic language
      - Template connective prose stripped to comma-separated chunks
      - Final assembly order tightened for latent-efficient density
      - Lighting expressed as cinematic lighting vocabulary
      - Render quality markers converted to visual material language
      - Space prompts anchored with physical geometry references

    All architecture features preserved:
      1. Mood compatibility filtering (mood × theme, mood × condition)
      2. Scene density clutter suppression
      3. Subject stability → render medium weighting
      4. Environmental diversity decay (anti-repetition)
      5. Camera angle integrated into assembly and DNA
      6. Render medium stability intelligence
      7. Trait pair memory scaffolding
      8. Expanded semantic template cadence
    """

    # -------------------------------------------------------------------------
    # Module-level shared state (persists across instances within a process)
    # -------------------------------------------------------------------------

    _diversity = DiversityTracker()
    _pair_memory = TraitPairMemory()

    # -------------------------------------------------------------------------
    # Weighted selection helper
    # -------------------------------------------------------------------------

    def pick_weighted(
        self,
        items: list[dict],
        key: str = "weight",
    ) -> dict:
        if not items:
            raise RuntimeError("Attempted weighted selection from empty list.")
        weights = [i.get(key, 1.0) for i in items]
        return random.choices(items, weights=weights, k=1)[0]

    # -------------------------------------------------------------------------
    # Density-aware weighted selection — v2.3
    # -------------------------------------------------------------------------

    DENSITY_OVERRIDE_PROB = 0.10

    def pick_weighted_with_density(
        self,
        items: list[dict],
        current_density: int,
        key: str = "weight",
    ) -> dict:
        if current_density < MAX_SCENE_DENSITY:
            return self.pick_weighted(items, key=key)

        if random.random() < self.DENSITY_OVERRIDE_PROB:
            return self.pick_weighted(items, key=key)

        adjusted = []
        for item in items:
            d = item.get("density_score", 0)
            if d <= 1:
                adjusted.append(item)
            else:
                penalty = max(item[key] * 0.15, 0.01)
                adjusted.append({**item, key: penalty})

        return self.pick_weighted(adjusted, key=key)

    # -------------------------------------------------------------------------
    # Mood → scene-semantic translation
    #
    # SDXL language note:
    #   Fields now contain visual descriptor chunks rather than abstract
    #   cinematic prose. The chosen field injects directly into the final
    #   prompt as a latent-efficient visual modifier.
    # -------------------------------------------------------------------------

    _MOOD_FIELD_WEIGHTS = [
        ("atmosphere", 0.55),
        ("motion",     0.25),
        ("density",    0.20),
    ]

    def _translate_mood(self, mood_label: str) -> str:
        data = MOOD_SEMANTICS.get(mood_label)
        if data is None:
            return mood_label
        fields, weights = zip(*self._MOOD_FIELD_WEIGHTS)
        chosen_field = random.choices(fields, weights=weights, k=1)[0]
        return data[chosen_field]

    # -------------------------------------------------------------------------
    # Scene suffix
    # -------------------------------------------------------------------------

    def _apply_scene_suffix(self, semantic: str, template: dict) -> str:
        if not template.get("uses_suffix", False):
            return semantic
        suffix_entry = self.pick_weighted(SCENE_SUFFIX)
        label = suffix_entry["label"].strip()
        if label:
            semantic = f"{semantic}, {label}"
        return semantic

    # -------------------------------------------------------------------------
    # Final prompt cleanup
    # -------------------------------------------------------------------------

    @staticmethod
    def _cleanup_prompt(prompt: str) -> str:
        prompt = re.sub(r"[,\s]*,[,\s]*", ", ", prompt)
        prompt = re.sub(r",\s*([.!?])", r"\1", prompt)
        prompt = re.sub(r" {2,}", " ", prompt)
        prompt = re.sub(r"[, ]+$", "", prompt)
        prompt = re.sub(
            r"\b(.+?),\s+\1\b",
            r"\1",
            prompt,
            flags=re.IGNORECASE,
        )
        return prompt.strip()

    # -------------------------------------------------------------------------
    # Lighting phrase assembly
    #
    # SDXL language note:
    #   Combines time and quality into cinematic lighting vocabulary.
    #   Format: "{time}, {quality}" → e.g. "golden hour, rim-lit silhouette"
    #   Both labels have been updated in constants to use photographic
    #   terminology rather than physical optics descriptions.
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_lighting_phrase(light_time: dict, light_quality: dict) -> str:
        return f"{light_time['label']}, {light_quality['label']}"

    # -------------------------------------------------------------------------
    # Taste bias — multiplies pick weights by learned per-trait multipliers
    # -------------------------------------------------------------------------

    TASTE_TRAITS = (
        "theme", "subject", "location", "environment", "light_time", "light_quality",
        "mood", "framing", "lens", "camera_angle", "render_medium", "quality_marker",
        "environmental_condition",
    )

    @staticmethod
    def _taste_multiplier(taste: dict | None, trait: str, label: str) -> float:
        return (taste or {}).get(trait, {}).get(label, 1.0)

    def _apply_taste(
        self,
        items: list[dict],
        trait: str,
        taste: dict | None,
    ) -> list[dict]:
        if not taste:
            return items
        return [
            {**item, "weight": item.get("weight", 1.0) * self._taste_multiplier(taste, trait, item["label"])}
            for item in items
        ]

    # -------------------------------------------------------------------------
    # Context-aware lighting bias — soft nudge, never a filter
    # -------------------------------------------------------------------------

    CONTEXT_BIAS_MULTIPLIER = 3.0

    _CONTEXT_LIGHT_BIAS = {
        "morning":   {"pre-dawn blue hour", "golden hour"},
        "afternoon": {"harsh noon", "deep overcast midday", "flat grey diffuse"},
        "evening":   {"golden hour", "twilight"},
        "night":     {"full dark", "twilight", "pre-dawn blue hour"},
        "winter":    {"flat grey diffuse", "deep overcast midday", "pre-dawn blue hour"},
        "spring":    {"golden hour", "pre-dawn blue hour"},
        "summer":    {"harsh noon", "golden hour"},
        "autumn":    {"golden hour", "twilight"},
    }

    def _bias_lighting_for_context(
        self,
        pool: list[dict],
        context: dict | None,
    ) -> list[dict]:
        if not context:
            return pool
        favored: set[str] = set()
        for key in ("time_of_day", "season"):
            favored |= self._CONTEXT_LIGHT_BIAS.get(context.get(key), set())
        if not favored:
            return pool
        return [
            {**item, "weight": item["weight"] * self.CONTEXT_BIAS_MULTIPLIER}
            if item["label"] in favored else item
            for item in pool
        ]

    # -------------------------------------------------------------------------
    # Main generation entry point — v2.3
    # -------------------------------------------------------------------------

    def generate(self, context: dict | None = None, taste: dict | None = None) -> dict[str, object]:

        if taste:
            theme_items = self._apply_taste(
                [{"label": name, "weight": 1.0} for name in THEMES],
                "theme",
                taste,
            )
            theme_name = self.pick_weighted(theme_items)["label"]
        else:
            theme_name = random.choice(list(THEMES.keys()))
        logging.info("V2.3 THEME: %s", theme_name)
        theme_data = THEMES[theme_name]

        # ------------------------------------------------------------------
        # 1. Subject — typed + stability class
        # ------------------------------------------------------------------
        subject = random.choices(
            theme_data["subjects"],
            weights=[w * self._taste_multiplier(taste, "subject", s["label"]) for s, w in zip(theme_data["subjects"], theme_data["subject_weights"])],
            k=1,
        )[0]
        subject_type      = subject["type"]
        subject_stability = subject.get("stability", "stable")

        scene_density = subject.get("density_score", 0)

        # ------------------------------------------------------------------
        # 2. Location — filtered by subject type
        # ------------------------------------------------------------------
        valid_locations = [
            loc for loc in theme_data["locations"]
            if subject_type in loc["valid_for"]
        ]
        valid_locations = self._apply_taste(valid_locations, "location", taste)
        location = self.pick_weighted_with_density(valid_locations, scene_density)
        scene_density += location.get("density_score", 0)

        # ------------------------------------------------------------------
        # 3. Environment — with density guard + diversity decay
        # ------------------------------------------------------------------
        environments = self._diversity.apply_decay(
            category="environment",
            items=theme_data["environments"],
        )
        environments = self._apply_taste(environments, "environment", taste)
        environment = self.pick_weighted_with_density(environments, scene_density)
        scene_density += environment.get("density_score", 0)

        # ------------------------------------------------------------------
        # 4. Lighting — time then quality, with diversity decay
        # ------------------------------------------------------------------
        if theme_name == "space":
            time_pool_raw = LIGHTING_TIME["space_only"]
        else:
            time_pool_raw = LIGHTING_TIME["universal"]

        time_pool = self._diversity.apply_decay(
            category="light_time",
            items=time_pool_raw,
        )
        time_pool = self._bias_lighting_for_context(time_pool, context)
        time_pool = self._apply_taste(time_pool, "light_time", taste)
        light_time = self.pick_weighted(time_pool)

        quality_pool_raw = [
            q for q in LIGHT_QUALITY
            if is_lighting_compatible(light_time["label"], q["label"])
        ]
        quality_pool = self._diversity.apply_decay(
            category="light_quality",
            items=quality_pool_raw,
        )
        quality_pool = self._apply_taste(quality_pool, "light_quality", taste)
        light_quality = self.pick_weighted(quality_pool)

        # ------------------------------------------------------------------
        # 5. Mood — with theme compatibility weighting
        # ------------------------------------------------------------------
        mood_pool = []
        for entry in get_mood_list():
            adjusted_weight = apply_mood_theme_weight(
                mood_label=entry["label"],
                theme_name=theme_name,
                base_weight=entry["weight"],
            )
            mood_pool.append({"label": entry["label"], "weight": adjusted_weight})

        mood_pool = self._apply_taste(mood_pool, "mood", taste)
        mood_entry = self.pick_weighted(mood_pool)
        mood_label = mood_entry["label"]

        # ------------------------------------------------------------------
        # 6. Composition — framing with density guard
        # ------------------------------------------------------------------
        valid_framings = [
            f for f in FRAMING_TYPE
            if subject_type in f["valid_for"]
        ]
        valid_framings = self._apply_taste(valid_framings, "framing", taste)
        framing = self.pick_weighted_with_density(valid_framings, scene_density)
        scene_density += framing.get("density_score", 0)

        valid_lenses = [
            lens for lens in LENS_CHARACTER
            if is_lens_framing_compatible(lens["label"], framing["label"])
        ]
        valid_lenses = self._apply_taste(valid_lenses, "lens", taste)
        lens = self.pick_weighted(valid_lenses)

        # ------------------------------------------------------------------
        # 7. Camera angle — filtered by framing + subject affinity boost
        # ------------------------------------------------------------------
        valid_angles = [
            angle for angle in CAMERA_ANGLE
            if is_camera_angle_framing_compatible(angle["label"], framing["label"])
        ]

        boosted_angles = []
        for angle in valid_angles:
            boost = get_camera_angle_affinity_boost(angle["label"], subject_type)
            boosted_angles.append({**angle, "weight": angle["weight"] * boost})

        boosted_angles = self._apply_taste(boosted_angles, "camera_angle", taste)
        camera_angle = self.pick_weighted(boosted_angles)

        # ------------------------------------------------------------------
        # 8. Render medium — stability-adjusted
        # ------------------------------------------------------------------
        valid_render_raw = [
            render for render in RENDER_MEDIUM
            if subject_type not in render.get("incompatible_subject_types", [])
            and theme_name not in render.get("incompatible_themes", [])
        ]
        valid_render_stable = apply_render_stability(valid_render_raw, subject_stability)
        valid_render_stable = self._apply_taste(valid_render_stable, "render_medium", taste)
        render_medium = self.pick_weighted(valid_render_stable)

        # ------------------------------------------------------------------
        # 9. Quality marker
        # ------------------------------------------------------------------
        valid_quality_markers = [
            marker for marker in RENDER_QUALITY_MARKERS
            if any(
                material in marker["valid_for"]
                for material in subject["material_class"]
            )
            and render_medium["label"] not in marker.get("incompatible_render", [])
        ]
        valid_quality_markers = self._apply_taste(valid_quality_markers, "quality_marker", taste)
        quality_marker = self.pick_weighted(valid_quality_markers)

        # ------------------------------------------------------------------
        # 10. Environmental condition — mood × condition compatibility
        # ------------------------------------------------------------------
        condition_pool_raw = get_environmental_condition(theme_name)

        condition_pool_mood = []
        for cond in condition_pool_raw:
            adjusted_weight = apply_mood_condition_weight(
                mood_label=mood_label,
                condition_label=cond["label"],
                base_weight=cond["weight"],
            )
            condition_pool_mood.append({**cond, "weight": adjusted_weight})

        condition_pool = self._diversity.apply_decay(
            category="environmental_condition",
            items=condition_pool_mood,
        )

        condition_pool = self._apply_taste(condition_pool, "environmental_condition", taste)
        environmental_condition = self.pick_weighted_with_density(
            condition_pool, scene_density
        )
        scene_density += environmental_condition.get("density_score", 0)

        # ------------------------------------------------------------------
        # 11. Semantic template — typed to subject
        # ------------------------------------------------------------------
        templates = SEMANTIC_TEMPLATES_BY_TYPE[subject_type]
        semantic_template = self.pick_weighted(templates)

        # ------------------------------------------------------------------
        # 12. Render template
        # ------------------------------------------------------------------
        render_template = self.pick_weighted(RENDER_TEMPLATES)

        # ------------------------------------------------------------------
        # Assemble semantic clause
        # ------------------------------------------------------------------
        template_string = semantic_template["template"]

        template_data: dict[str, str] = {
            "subject":     subject["label"],
            "location":    location["label"],
            "environment": environment["label"],
        }

        if semantic_template.get("uses_condition"):
            template_data["condition"] = environmental_condition["label"]

        if semantic_template.get("uses_camera_angle"):
            template_data["camera_angle"] = camera_angle["label"]

        semantic = template_string.format(**template_data)
        semantic = self._apply_scene_suffix(semantic, semantic_template)

        # ------------------------------------------------------------------
        # Assemble render clause
        # ------------------------------------------------------------------
        render = render_template["template"].format(
            render_medium=render_medium["label"],
            lens=lens["label"],
            quality_marker=quality_marker["label"],
        )

        # ------------------------------------------------------------------
        # Mood → visual descriptor chunk
        #
        # SDXL language note:
        #   _translate_mood now returns visually concrete descriptor strings
        #   (e.g. "empty ruins, no signs of life, overcast skies") rather
        #   than abstract cinematic descriptions. These inject as strong
        #   latent activators aligned with JuggernautXL training data.
        # ------------------------------------------------------------------
        mood_semantic = self._translate_mood(mood_label)

        # ------------------------------------------------------------------
        # Camera angle clause for prompt injection
        #
        # Only injected when NOT already embedded in the semantic template.
        # Uses SDXL-native photographic framing language.
        # ------------------------------------------------------------------
        camera_angle_clause = ""
        if not semantic_template.get("uses_camera_angle"):
            camera_angle_clause = camera_angle["label"]

        # ------------------------------------------------------------------
        # Lighting phrase
        # ------------------------------------------------------------------
        lighting_phrase = self._build_lighting_phrase(light_time, light_quality)

        # ------------------------------------------------------------------
        # Diversity tracker — push used labels
        # ------------------------------------------------------------------
        self._diversity.push("environment",            environment["label"])
        self._diversity.push("light_time",             light_time["label"])
        self._diversity.push("light_quality",          light_quality["label"])
        self._diversity.push("environmental_condition", environmental_condition["label"])

        # ------------------------------------------------------------------
        # Trait pair memory — record co-occurrences
        # ------------------------------------------------------------------
        dna_traits = [
            subject["label"],
            environment["label"],
            light_time["label"],
            light_quality["label"],
            mood_label,
            framing["label"],
            lens["label"],
            render_medium["label"],
            environmental_condition["label"],
            camera_angle["label"],
        ]
        self._pair_memory.record(dna_traits)

        # ------------------------------------------------------------------
        # DNA record
        # ------------------------------------------------------------------
        dna = {
            "theme":                    theme_name,
            "subject":                  subject["label"],
            "subject_type":             subject_type,
            "subject_stability":        subject_stability,
            "location":                 location["label"],
            "environment":              environment["label"],
            "mood":                     mood_label,
            "light_time":               light_time["label"],
            "light_quality":            light_quality["label"],
            "framing":                  framing["label"],
            "lens":                     lens["label"],
            "camera_angle":             camera_angle["label"],
            "render_medium":            render_medium["label"],
            "quality_marker":           quality_marker["label"],
            "environmental_condition":  environmental_condition["label"],
            "scene_density_score":      scene_density,
        }

        # ------------------------------------------------------------------
        # Final prompt assembly — v2.3 SDXL-optimized
        #
        # Layer order (latent-priority sequence):
        #   semantic clause          → primary subject + location + environment
        #   mood descriptor          → atmosphere / motion / density visual chunk
        #   lighting phrase          → cinematic lighting vocabulary
        #   framing label            → composition cue
        #   camera angle clause      → photographic angle (if not in template)
        #   render clause            → medium + lens + quality marker
        #
        # SDXL language note:
        #   Assembly uses comma-separated visual chunks throughout.
        #   No prose connectives, no "and then", no literary transitions.
        #   Each layer is a discrete latent-activating descriptor group.
        #   Total prompt length targets 12–18 strong visual concepts.
        #   Redundancy suppressed by _cleanup_prompt deduplication pass.
        # ------------------------------------------------------------------

        parts = [
            semantic,
            mood_semantic,
            lighting_phrase,
            framing["label"],
        ]

        if camera_angle_clause:
            parts.append(camera_angle_clause)

        parts.append(render)

        prompt = ", ".join(parts)
        prompt = self._cleanup_prompt(prompt)

        logging.debug(
            "V2.3 DENSITY: %d | STABILITY: %s | RENDER: %s",
            scene_density,
            subject_stability,
            render_medium["label"],
        )

        return {
            "semantic_prompt": semantic,
            "render_prompt":   render,
            "final_prompt":    prompt,
            "dna":             dna,
        }