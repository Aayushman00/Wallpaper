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


class ContextPromptEngine:
    def __init__(self):
        self.contexts = []

    def generate(self, context=None):
        self.contexts.append(context)
        return {
            "final_prompt": "a cinematic castle",
            "semantic_prompt": "a castle",
            "dna": {"theme": "fantasy"},
        }


class FakeSeedPool:
    def __init__(self):
        self.recorded = []
        self.recorded_lineage = []
        self.penalized = []

    def penalize(self, seeds):
        self.penalized.append(seeds)

    def record_result(self, seeds, score, prompt, theme, lineage=None):
        self.recorded.append((seeds, score, prompt, theme))
        self.recorded_lineage.append(lineage)


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


def _make_engine(gpu_monitor, backend, evaluator_factories_called, aesthetic=6.0, prompt_engine=None):
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
                return aesthetic
        return _Fake()

    return WallpaperEngine(
        backend=backend,
        prompt_engine=prompt_engine or FakePromptEngine(),
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
        used_lineage=[(None, 0), (41, 2)],
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
    assert engine.seed_pool.recorded_lineage == [[(None, 0), (41, 2)]]


def _result(tmp_path, lineage=None):
    return GenerationResult(
        image_path=tmp_path / "wallpapers" / "out.png",
        used_seeds=[42, 43],
        generation_time_seconds=1.5,
        used_lineage=lineage if lineage is not None else [(None, 0), (41, 2)],
    )


def test_run_returns_none_when_cycle_is_skipped():
    engine = _make_engine(FakeGPUMonitor([False] * 5), FakeBackend(), [])

    assert engine.run() is None


def test_run_returns_cycle_result_with_max_generation(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [])

    cycle = engine.run()

    assert cycle.image_path == result.image_path
    assert cycle.used_seeds == [42, 43]
    assert cycle.generation == 2
    assert cycle.quarantined is False


def test_run_quarantines_image_below_quality_floor(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [], aesthetic=3.9)

    cycle = engine.run()

    assert cycle.quarantined is True
    assert engine.seed_pool.penalized == [[42, 43]]
    assert engine.seed_pool.recorded == []
    assert engine.wallpaper_service.set_calls == []
    assert engine.history_repository.appended[0]["quarantined"] is True


def test_run_does_not_quarantine_at_exactly_the_floor(tmp_path):
    result = _result(tmp_path)
    engine = _make_engine(FakeGPUMonitor([True]), FakeBackend(result=result), [], aesthetic=4.0)

    cycle = engine.run()

    assert cycle.quarantined is False
    assert engine.wallpaper_service.set_calls == [result.image_path]
    assert engine.history_repository.appended[0]["quarantined"] is False


def test_run_passes_context_to_prompt_engine_only_when_given(tmp_path):
    prompt_engine = ContextPromptEngine()
    result = _result(tmp_path)
    engine = _make_engine(
        FakeGPUMonitor([True, True]), FakeBackend(result=result), [], prompt_engine=prompt_engine,
    )

    engine.run(context={"time_of_day": "night"})
    engine.run()

    assert prompt_engine.contexts == [{"time_of_day": "night"}, None]
