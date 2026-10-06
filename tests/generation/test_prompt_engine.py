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
