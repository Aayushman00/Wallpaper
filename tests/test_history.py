from database.history import HistoryRepository

def test_history_entry_saved(tmp_path):

    history_file = tmp_path / "history.json"

    repo = HistoryRepository(history_file)

    repo.append(
        prompt="space wallpaper",
        seeds=[111],
        score=55.5,
        image_path="test.png",
        generation_time=5.2,
    )

    records = repo.load()

    assert len(records) == 1

    assert records[0]["prompt"] == "space wallpaper"

    assert records[0]["score"] == 55.5