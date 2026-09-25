from generation.prompt_engine import PromptEngine
from config.prompt_grammar import THEMES


def test_generate_returns_expected_shape():
    engine = PromptEngine()

    result = engine.generate()

    assert isinstance(result, dict)
    assert len(result["final_prompt"]) > 0
    assert result["dna"]["theme"] in THEMES
