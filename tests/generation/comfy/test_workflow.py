import json

from generation.comfy.workflow import WorkflowManager


class FakeSeedPool:
    def __init__(self, seeds):
        self._seeds = iter(seeds)
        self.calls = 0

    def next_seed(self):
        self.calls += 1
        return next(self._seeds)


def _write_fake_workflow(path):
    workflow = {
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "8": {"class_type": "KSampler", "inputs": {"seed": 0, "cfg": 0, "steps": 0, "sampler_name": ""}},
        "17": {"class_type": "KSampler", "inputs": {"seed": 0, "cfg": 0, "steps": 0, "denoise": 0, "sampler_name": ""}},
        "20": {"class_type": "LatentUpscaleBy", "inputs": {"scale_by": 0}},
        "23": {"class_type": "ImageSharpen", "inputs": {"alpha": 0}},
    }
    path.write_text(json.dumps(workflow), encoding="utf-8")


def test_prepare_pulls_one_seed_per_ksampler_and_injects_prompt(tmp_path):
    workflow_path = tmp_path / "wallpaper.json"
    _write_fake_workflow(workflow_path)
    seeds = FakeSeedPool([111, 222])

    manager = WorkflowManager(workflow_path, seeds)
    workflow, used_seeds = manager.prepare(
        final_prompt="a cinematic castle",
        dna={"theme": "fantasy", "scene_density_score": 5, "subject_type": "structure", "mood": "mythic and ancient"},
    )

    assert seeds.calls == 2
    assert used_seeds == [111, 222]
    assert workflow["6"]["inputs"]["text"] == "a cinematic castle"
    assert workflow["8"]["inputs"]["seed"] == 111
    assert workflow["17"]["inputs"]["seed"] == 222


def test_prepare_raises_when_no_ksampler_present(tmp_path):
    workflow_path = tmp_path / "wallpaper.json"
    workflow_path.write_text(json.dumps({"6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}}}), encoding="utf-8")
    seeds = FakeSeedPool([111])

    manager = WorkflowManager(workflow_path, seeds)

    import pytest
    with pytest.raises(RuntimeError, match="No KSampler node found"):
        manager.prepare(final_prompt="x", dna={"theme": "fantasy"})
