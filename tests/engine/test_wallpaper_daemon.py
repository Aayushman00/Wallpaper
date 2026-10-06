import json
import time
from pathlib import Path

from engine.models import CycleResult
from engine.wallpaper_daemon import WallpaperDaemon


class FakeEngine:
    def __init__(self, results=None, fail_first=False):
        self.results = list(results or [])
        self.fail_first = fail_first
        self.contexts = []
        self.runs = 0

    def run(self, context=None):
        self.runs += 1
        self.contexts.append(context)
        if self.fail_first and self.runs == 1:
            raise RuntimeError("bad cycle")
        return self.results.pop(0) if self.results else None


class FakeSeedPool:
    def __init__(self):
        self.rated = []

    def rate_current(self, seeds, liked):
        self.rated.append((seeds, liked))


class FakeHistory:
    def __init__(self, entries=()):
        self.entries = list(entries)

    def load(self):
        return self.entries


class FakeWallpaperService:
    def __init__(self):
        self.set_calls = []

    def set_wallpaper(self, path):
        self.set_calls.append(path)


class FakeListener:
    def __init__(self, bindings):
        self.bindings = bindings
        self.stopped = False

    def run(self):
        pass

    def stop(self):
        self.stopped = True


def _cycle(seeds=(1, 2), generation=3, quarantined=False, path="wallpapers/new.png"):
    return CycleResult(Path(path), list(seeds), generation, quarantined)


def _daemon(tmp_path, engine=None, history=None, fullscreen=lambda: False, interval=0.01, recheck=0.01):
    return WallpaperDaemon(
        engine=engine or FakeEngine(),
        seed_pool=FakeSeedPool(),
        history_repository=history or FakeHistory(),
        wallpaper_service=FakeWallpaperService(),
        state_path=tmp_path / "current_state.json",
        is_fullscreen=fullscreen,
        get_context=lambda: {"time_of_day": "night", "season": "winter"},
        interval=interval,
        recheck=recheck,
        listener_factory=FakeListener,
    )


def wait_until(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# --- state & rating -------------------------------------------------------

def test_successful_cycle_passes_context_and_persists_state(tmp_path):
    engine = FakeEngine([_cycle()])
    daemon = _daemon(tmp_path, engine)

    daemon.run_cycle()

    assert engine.contexts == [{"time_of_day": "night", "season": "winter"}]
    expected = {"seeds": [1, 2], "image_path": str(Path("wallpapers/new.png")), "generation": 3}
    assert daemon.state == expected
    assert json.loads((tmp_path / "current_state.json").read_text()) == expected


def test_state_is_reloaded_by_a_new_daemon(tmp_path):
    _daemon(tmp_path, FakeEngine([_cycle()])).run_cycle()

    reloaded = _daemon(tmp_path)

    assert reloaded.state["seeds"] == [1, 2]


def test_corrupt_state_file_is_ignored(tmp_path):
    (tmp_path / "current_state.json").write_text("{not json")

    assert _daemon(tmp_path).state is None


def test_quarantined_cycle_leaves_state_pointing_at_last_displayed_image(tmp_path):
    engine = FakeEngine([_cycle(seeds=(1, 2)), _cycle(seeds=(8, 9), quarantined=True)])
    daemon = _daemon(tmp_path, engine)

    daemon.run_cycle()
    daemon.run_cycle()
    daemon.like()

    assert daemon.state["seeds"] == [1, 2]
    assert daemon.seed_pool.rated == [([1, 2], True)]


def test_skipped_cycle_leaves_state_untouched(tmp_path):
    daemon = _daemon(tmp_path, FakeEngine([None]))

    daemon.run_cycle()

    assert daemon.state is None


def test_like_and_dislike_rate_current_seeds(tmp_path):
    daemon = _daemon(tmp_path, FakeEngine([_cycle()]))
    daemon.run_cycle()

    daemon.like()
    daemon.dislike()

    assert daemon.seed_pool.rated == [([1, 2], True), ([1, 2], False)]


def test_rating_without_current_state_is_a_noop(tmp_path):
    daemon = _daemon(tmp_path)

    daemon.like()
    daemon.dislike()

    assert daemon.seed_pool.rated == []


# --- revert ---------------------------------------------------------------

def test_revert_sets_second_to_last_non_quarantined_image(tmp_path):
    older, newer = tmp_path / "older.png", tmp_path / "newer.png"
    older.write_bytes(b"x")
    newer.write_bytes(b"x")
    history = FakeHistory([
        {"image_path": str(older)},
        {"image_path": str(newer)},
        {"image_path": "bad.png", "quarantined": True},
    ])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == [older]
    assert daemon.seed_pool.rated == []


def test_revert_with_fewer_than_two_usable_entries_is_a_noop(tmp_path):
    history = FakeHistory([{"image_path": "a.png"}, {"image_path": "b.png", "quarantined": True}])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == []


def test_revert_when_target_image_is_missing_is_a_noop(tmp_path):
    newer = tmp_path / "newer.png"
    newer.write_bytes(b"x")
    history = FakeHistory([{"image_path": str(tmp_path / "gone.png")}, {"image_path": str(newer)}])
    daemon = _daemon(tmp_path, history=history)

    daemon.revert()

    assert daemon.wallpaper_service.set_calls == []


# --- scheduler thread -----------------------------------------------------

def test_scheduler_runs_cycles_on_the_interval_and_stops(tmp_path):
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine)

    daemon.start()
    assert wait_until(lambda: engine.runs >= 2)
    daemon.stop()

    assert not daemon._scheduler.is_alive()
    assert daemon._listener.stopped is True


def test_scheduler_survives_a_cycle_that_raises(tmp_path):
    engine = FakeEngine(fail_first=True)
    daemon = _daemon(tmp_path, engine)

    daemon.start()
    assert wait_until(lambda: engine.runs >= 2)
    assert daemon._scheduler.is_alive()
    daemon.stop()


def test_scheduler_defers_while_fullscreen_then_runs(tmp_path):
    engine = FakeEngine()
    state = {"fullscreen": True}
    daemon = _daemon(tmp_path, engine, fullscreen=lambda: state["fullscreen"])

    daemon.start()
    time.sleep(0.15)
    assert engine.runs == 0

    state["fullscreen"] = False
    assert wait_until(lambda: engine.runs >= 1)
    daemon.stop()


def test_generate_next_bypasses_focus_assist_and_the_interval(tmp_path):
    engine = FakeEngine()
    daemon = _daemon(tmp_path, engine, fullscreen=lambda: True, interval=60, recheck=60)

    daemon.start()
    time.sleep(0.05)
    assert engine.runs == 0

    daemon.generate_next()
    assert wait_until(lambda: engine.runs == 1)
    daemon.stop()


def test_stop_interrupts_a_long_sleep_promptly(tmp_path):
    daemon = _daemon(tmp_path, interval=60)
    daemon.start()

    started = time.time()
    daemon.stop()

    assert time.time() - started < 2.0
    assert not daemon._scheduler.is_alive()


# --- hotkey wiring --------------------------------------------------------

def test_hotkey_bindings_map_ctrl_alt_arrows_to_daemon_actions(tmp_path):
    from system.hotkeys import MOD_ALT, MOD_CONTROL, VK_DOWN, VK_LEFT, VK_RIGHT, VK_UP

    daemon = _daemon(tmp_path)
    daemon.start()
    bindings = {(mods, vk): cb for mods, vk, cb in daemon._listener.bindings}
    daemon.stop()

    ctrl_alt = MOD_CONTROL | MOD_ALT
    assert bindings[(ctrl_alt, VK_UP)] == daemon.like
    assert bindings[(ctrl_alt, VK_DOWN)] == daemon.dislike
    assert bindings[(ctrl_alt, VK_RIGHT)] == daemon.generate_next
    assert bindings[(ctrl_alt, VK_LEFT)] == daemon.revert
