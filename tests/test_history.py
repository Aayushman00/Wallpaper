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
