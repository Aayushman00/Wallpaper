from database.history import HistoryRepository

def test_history_entry_saved(tmp_path):

    history_file = tmp_path / "history.json"

    repo = HistoryRepository(history_file)

    repo.append(
        seeds=[111],
        semantic_score=55.5,
        aesthetic_score=70,
        combined_score=99,
        image_path="test.png",
        generation_time=5.2,
        dna={},
        semantic_prompt="space wallpaper",
    )

    records = repo.load()

    assert len(records) == 1

    assert records[0]["semantic_prompt"] == "space wallpaper"

    assert records[0]["combined_score"] == 99

def _append(repo, **extra):
    repo.append(
        seeds=[1], semantic_score=50.0, aesthetic_score=5.0, combined_score=0.5,
        image_path="a.png", generation_time=1.0, semantic_prompt="p", dna={}, **extra,
    )


def test_history_quarantined_flag_only_written_when_true(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")

    _append(repo)
    _append(repo, quarantined=True)

    normal, quarantined = repo.load()
    assert "quarantined" not in normal
    assert quarantined["quarantined"] is True


import threading

import pytest


def _append_image(repo, image_path):
    repo.append(
        seeds=[1], semantic_score=50.0, aesthetic_score=5.0, combined_score=0.5,
        image_path=image_path, generation_time=1.0, semantic_prompt="p", dna={},
    )


def test_set_rating_marks_the_newest_entry_for_that_image(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    _append_image(repo, "b.png")
    _append_image(repo, "a.png")

    assert repo.set_rating("a.png", 1) is True

    first, second, third = repo.load()
    assert "rating" not in first
    assert "rating" not in second
    assert third["rating"] == 1


def test_set_rating_replaces_an_earlier_rating_instead_of_compounding(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")

    repo.set_rating("a.png", 1)
    repo.set_rating("a.png", 1)
    assert repo.load()[0]["rating"] == 1

    repo.set_rating("a.png", -1)
    assert repo.load()[0]["rating"] == -1


def test_set_rating_for_unknown_image_returns_false_and_writes_nothing(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    before = repo.path.read_text(encoding="utf-8")

    assert repo.set_rating("missing.png", 1) is False

    assert repo.path.read_text(encoding="utf-8") == before


def test_set_rating_on_empty_history_returns_false(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")

    assert repo.set_rating("a.png", 1) is False


@pytest.mark.parametrize("bad", [0, 2, -2, True, False, 1.0, "1", None])
def test_set_rating_rejects_anything_but_plus_or_minus_one_and_writes_nothing(tmp_path, bad):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "a.png")
    before = repo.path.read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        repo.set_rating("a.png", bad)

    assert repo.path.read_text(encoding="utf-8") == before


def test_concurrent_append_and_set_rating_lose_nothing(tmp_path):
    repo = HistoryRepository(tmp_path / "history.json")
    _append_image(repo, "rated.png")

    def add(i):
        _append_image(repo, f"img{i}.png")

    def rate():
        for _ in range(20):
            repo.set_rating("rated.png", 1)

    threads = [threading.Thread(target=add, args=(i,)) for i in range(20)]
    threads.append(threading.Thread(target=rate))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    records = repo.load()
    assert len(records) == 21
    assert next(r for r in records if r["image_path"] == "rated.png")["rating"] == 1
