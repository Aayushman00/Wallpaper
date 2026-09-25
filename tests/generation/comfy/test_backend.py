from pathlib import Path

from engine.models import GenerationRequest
from generation.comfy.backend import ComfyBackend


class FakeWorkflowManager:
    def prepare(self, final_prompt, dna):
        return {"workflow": "payload"}, [42, 43]


class FakeFileManager:
    def move_generated_image(self, filename, subfolder):
        return Path("wallpapers") / filename


def test_generate_returns_generation_result_on_success():
    class FakeClient:
        def queue_prompt(self, workflow):
            return "prompt-id-1"

        def wait_for_image(self, prompt_id):
            assert prompt_id == "prompt-id-1"
            return {"filename": "out.png", "subfolder": "sub"}

    backend = ComfyBackend(
        client=FakeClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
    )

    assert result is not None
    assert result.image_path == Path("wallpapers/out.png")
    assert result.used_seeds == [42, 43]
    assert result.generation_time_seconds >= 0


def test_generate_does_not_require_a_seeds_argument():
    class FakeClient:
        def queue_prompt(self, workflow):
            return "prompt-id-1"

        def wait_for_image(self, prompt_id):
            return {"filename": "out.png", "subfolder": "sub"}

    backend = ComfyBackend(
        client=FakeClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}))

    assert result is not None
    assert result.used_seeds == [42, 43]


def test_generate_returns_none_when_queue_fails():
    class FailingClient:
        def queue_prompt(self, workflow):
            return None

        def wait_for_image(self, prompt_id):
            raise AssertionError("should not be called")

    backend = ComfyBackend(
        client=FailingClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
    )

    assert result is None


def test_generate_returns_none_when_image_wait_fails():
    class TimeoutClient:
        def queue_prompt(self, workflow):
            return "prompt-id-1"

        def wait_for_image(self, prompt_id):
            return None

    backend = ComfyBackend(
        client=TimeoutClient(),
        server=None,
        workflow=FakeWorkflowManager(),
        file_manager=FakeFileManager(),
    )

    result = backend.generate(
        GenerationRequest(prompt="a cat", dna={"theme": "fantasy"}),
    )

    assert result is None


def test_ensure_ready_returns_true_when_already_running():
    class RunningServer:
        def is_running(self):
            return True

        def start(self):
            raise AssertionError("should not start when already running")

    backend = ComfyBackend(
        client=None, server=RunningServer(), workflow=None, file_manager=None,
    )

    assert backend.ensure_ready() is True


def test_ensure_ready_starts_server_and_waits_for_boot():
    class BootingServer:
        def __init__(self):
            self.checks = 0
            self.started = False

        def is_running(self):
            self.checks += 1
            if not self.started:
                return False
            return self.checks > 2

        def start(self):
            self.started = True

    backend = ComfyBackend(
        client=None, server=BootingServer(), workflow=None, file_manager=None,
        sleep=lambda seconds: None,
    )

    assert backend.ensure_ready() is True


def test_ensure_ready_returns_false_when_server_never_boots():
    class NeverBootsServer:
        def is_running(self):
            return False

        def start(self):
            pass

    backend = ComfyBackend(
        client=None, server=NeverBootsServer(), workflow=None, file_manager=None,
        sleep=lambda seconds: None,
    )

    assert backend.ensure_ready() is False
