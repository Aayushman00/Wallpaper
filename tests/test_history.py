from database.history import HistoryRepository

def test_history_file_created(tmp_path):

    history_file = (
        tmp_path / "history.json"
    )

    repo = HistoryRepository(history_file)

    repo.append(
        prompt="test",
        seeds=[123],
        score=50.0,
        image_path="test.png",
        generation_time=1.2,
    )

    assert history_file.exists()