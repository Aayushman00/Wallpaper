from pathlib import Path

from engine.models import GenerationRequest, GenerationResult, EvaluationResult


def test_generation_request_holds_prompt_and_dna():
    req = GenerationRequest(prompt="a cat", dna={"theme": "fantasy"})
    assert req.prompt == "a cat"
    assert req.dna == {"theme": "fantasy"}


def test_generation_result_holds_output_shape():
    result = GenerationResult(
        image_path=Path("wallpapers/foo.png"),
        used_seeds=[1, 2],
        generation_time_seconds=12.5,
    )
    assert result.image_path == Path("wallpapers/foo.png")
    assert result.used_seeds == [1, 2]
    assert result.generation_time_seconds == 12.5


def test_evaluation_result_holds_scores():
    result = EvaluationResult(semantic_score=80.0, aesthetic_score=6.5, combined_score=5.9)
    assert result.semantic_score == 80.0
    assert result.aesthetic_score == 6.5
    assert result.combined_score == 5.9
