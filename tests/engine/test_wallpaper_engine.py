from pathlib import Path

from engine.wallpaper_engine import WallpaperEngine
from engine.models import GenerationResult


class FakeGPUMonitor:
    def __init__(self, idle_sequence):
        self._sequence = iter(idle_sequence)

    def is_idle(self):
        return next(self._sequence)


class FakeBackend:
    def __init__(self, ready=True, result=None):
        self._ready = ready
        self._result = result
        self.generate_calls = []

    def ensure_ready(self):
        return self._ready

    def generate(self, request):
        self.generate_calls.append(request)
        return self._result


class FakePromptEngine:
    def generate(self):
        return {
            "final_prompt": "a cinematic castle",
            "semantic_prompt": "a castle",
            "dna": {"theme": "fantasy"},
        }


class FakeSeedPool:
    def __init__(self):
        self.recorded = []

    def record_result(self, seeds, score, prompt, theme):
        self.recorded.append((seeds, score, prompt, theme))


class FakeHistoryRepository:
    def __init__(self):
        self.appended = []

    def append(self, **kwargs):
        self.appended.append(kwargs)


class FakeWallpaperService:
    def __init__(self):
        self.set_calls = []

    def set_wallpaper(self, path):
        self.set_calls.append(path)


def _make_engine(gpu_monitor, backend, evaluator_factories_called):
    def semantic_factory():
        evaluator_factories_called.append("semantic")
        class _Fake:
            def score(self, path, prompt):
                return 80.0
        return _Fake()

    def aesthetic_factory():
        evaluator_factories_called.append("aesthetic")
        class _Fake:
            def score(self, path):
                return 6.0
        return _Fake()

    return WallpaperEngine(
        backend=backend,
        prompt_engine=FakePromptEngine(),
        seed_pool=FakeSeedPool(),
        history_repository=FakeHistoryRepository(),
        wallpaper_service=FakeWallpaperService(),
        gpu_monitor=gpu_monitor,
        semantic_scorer_factory=semantic_factory,
        aesthetic_scorer_factory=aesthetic_factory,
        sleep=lambda seconds: None,
    )


def test_run_skips_when_gpu_never_idles():
    calls = []
    backend = FakeBackend()
    engine = _make_engine(FakeGPUMonitor([False] * 5), backend, calls)

    engine.run()

    assert backend.generate_calls == []
    assert calls == []


def test_run_returns_when_comfy_fails_to_boot():
    calls = []
    backend = FakeBackend(ready=False)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert backend.generate_calls == []
    assert calls == []


def test_run_returns_when_generation_fails():
    calls = []
    backend = FakeBackend(ready=True, result=None)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert len(backend.generate_calls) == 1
    assert calls == []


def test_run_happy_path_scores_persists_and_sets_wallpaper(tmp_path):
    calls = []
    result = GenerationResult(
        image_path=tmp_path / "wallpapers" / "out.png",
        used_seeds=[42, 43],
        generation_time_seconds=1.5,
    )
    backend = FakeBackend(ready=True, result=result)
    engine = _make_engine(FakeGPUMonitor([True]), backend, calls)

    engine.run()

    assert calls == ["semantic", "aesthetic"]
    assert engine.seed_pool.recorded[0][0] == [42, 43]
    combined = 0.4 * (80.0 / 100) + 0.6 * (6.0 / 10)
    assert round(engine.seed_pool.recorded[0][1], 4) == round(combined, 4)
    assert engine.history_repository.appended[0]["combined_score"] == engine.seed_pool.recorded[0][1]
    assert engine.wallpaper_service.set_calls == [result.image_path]
