from config import settings


def test_infra_constants_present_and_correct():
    assert settings.COMFY_URL == "http://127.0.0.1:8188"
    assert settings.WORKFLOW_PROMPT_NODE_ID == "6"
    assert settings.WORKFLOW_KSAMPLER_FIRST_NODE_ID == "8"
    assert settings.WORKFLOW_KSAMPLER_SECOND_NODE_ID == "17"
    assert settings.WORKFLOW_LATENT_UPSCALE_NODE_ID == "20"
    assert settings.WORKFLOW_IMAGE_SHARPEN_NODE_ID == "23"
    assert settings.GPU_INDEX == "0"
    assert settings.GPU_IDLE_THRESHOLD == 50
    assert settings.GPU_IDLE_RETRIES == 5
    assert settings.GPU_IDLE_WAIT_SECONDS == 120
    assert settings.COMFY_BOOT_RETRIES == 30
    assert settings.COMFY_BOOT_WAIT_SECONDS == 2
    assert settings.GENERATION_TIMEOUT_SECONDS == 300
    assert settings.HISTORY_POLL_SECONDS == 2
    assert settings.BEST_SEED_MUTATION_RANGE == 5000
    assert settings.BEST_SEED_REUSE_PROBABILITY == 0.7
    assert settings.BEST_SEED_LIMIT == 50
