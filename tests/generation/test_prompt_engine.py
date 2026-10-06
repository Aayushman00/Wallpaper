from generation.prompt_engine import PromptEngine
from config.prompt_grammar import THEMES


def test_generate_returns_expected_shape():
    engine = PromptEngine()

    result = engine.generate()

    assert isinstance(result, dict)
    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES


POOL = [
    {"label": "golden hour", "weight": 0.2},
    {"label": "harsh noon", "weight": 0.2},
    {"label": "full dark", "weight": 0.2},
]


def test_generate_accepts_context_and_still_returns_expected_shape():
    result = PromptEngine().generate(context={"time_of_day": "night", "season": "winter"})

    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES


def test_bias_boosts_context_matching_lighting_without_filtering():
    biased = PromptEngine()._bias_lighting_for_context(POOL, {"time_of_day": "night", "season": "autumn"})

    weights = {item["label"]: item["weight"] for item in biased}
    assert weights["full dark"] > 0.2        # night favours full dark
    assert weights["golden hour"] > 0.2      # autumn favours golden hour
    assert weights["harsh noon"] == 0.2      # untouched
    assert len(biased) == len(POOL)          # soft bias, never a filter


def test_bias_does_not_mutate_input_pool():
    PromptEngine()._bias_lighting_for_context(POOL, {"time_of_day": "night"})

    assert [item["weight"] for item in POOL] == [0.2, 0.2, 0.2]


def test_bias_is_a_noop_without_or_with_unknown_context():
    engine = PromptEngine()

    assert engine._bias_lighting_for_context(POOL, None) == POOL
    assert engine._bias_lighting_for_context(POOL, {}) == POOL
    assert engine._bias_lighting_for_context(POOL, {"time_of_day": "teatime"}) == POOL


import random

import pytest

from config.prompt_grammar import MAX_SCENE_DENSITY
from config.settings import TASTE_MAX, TASTE_MIN

TASTE_POOL = [
    {"label": "a", "weight": 1.0},
    {"label": "b", "weight": 2.0},
    {"label": "c", "weight": 0.5},
]


def test_apply_taste_is_a_noop_without_taste():
    engine = PromptEngine()

    assert engine._apply_taste(TASTE_POOL, "mood", None) == TASTE_POOL
    assert engine._apply_taste(TASTE_POOL, "mood", {}) == TASTE_POOL


def test_apply_taste_scales_matching_labels_and_does_not_mutate_input():
    taste = {"mood": {"a": 1.5, "b": 0.4}}

    result = PromptEngine()._apply_taste(TASTE_POOL, "mood", taste)

    assert [i["weight"] for i in result] == pytest.approx([1.5, 0.8, 0.5])
    assert [i["weight"] for i in TASTE_POOL] == [1.0, 2.0, 0.5]


def test_apply_taste_ignores_other_traits_and_unknown_labels():
    result = PromptEngine()._apply_taste(TASTE_POOL, "mood", {"lens": {"a": 2.0}, "mood": {"zzz": 2.0}})

    assert result == TASTE_POOL


def test_generate_with_taste_returns_expected_shape():
    result = PromptEngine().generate(taste={"mood": {"nothing": 1.0}})

    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES


def test_generate_consults_taste_for_every_hooked_trait(monkeypatch):
    seen = set()
    original = PromptEngine._taste_multiplier

    def spy(taste, trait, label):
        seen.add(trait)
        return original(taste, trait, label)

    monkeypatch.setattr(PromptEngine, "_taste_multiplier", staticmethod(spy))

    result = PromptEngine().generate(taste={"mood": {"nothing": 1.0}})

    assert seen == set(PromptEngine.TASTE_TRAITS)
    assert set(PromptEngine.TASTE_TRAITS) <= set(result["dna"])


def test_taste_steers_theme_choice_toward_the_boosted_value():
    random.seed(1234)
    themes = list(THEMES)
    taste = {"theme": {name: (TASTE_MAX if name == themes[0] else TASTE_MIN) for name in themes}}
    engine = PromptEngine()

    picks = [engine.generate(taste=taste)["dna"]["theme"] for _ in range(300)]

    assert picks.count(themes[0]) / 300 > 1 / len(themes) + 0.15


@pytest.mark.parametrize("current_density", [0, MAX_SCENE_DENSITY])
def test_taste_steers_non_theme_picks_through_pick_weighted_with_density(current_density):
    random.seed(99)
    engine = PromptEngine()
    pool = [{"label": "liked", "weight": 1.0}, {"label": "disliked", "weight": 1.0}]
    taste = {"environment": {"liked": TASTE_MAX, "disliked": TASTE_MIN}}
    weighted = engine._apply_taste(pool, "environment", taste)

    picks = [
        engine.pick_weighted_with_density(weighted, current_density)["label"]
        for _ in range(500)
    ]

    # expected share 2.0 / (2.0 + 0.4) = 0.83, in both the normal and the density-guarded path
    assert picks.count("liked") / 500 > 0.7
