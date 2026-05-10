from core.prompt_engine import PromptEngine
import config.constants


def test_prompt_cotains_theme():

    engine = PromptEngine()

    prompt = engine.generate("cyberpunk")

    assert isinstance(prompt, dict)
    assert len(prompt["final_prompt"]) > 0
