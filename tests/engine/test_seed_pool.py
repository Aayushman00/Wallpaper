from engine.seed_pool import SeedPool
from database.seeds import SeedRepository


def test_next_seed_is_integer(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    seed = pool.next_seed()

    assert isinstance(seed, int)


def test_record_result_persists_ranked_by_score(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111, 222], score=0.9, prompt="a cat", theme="fantasy")
    pool.record_result(seeds=[333], score=0.1, prompt="a dog", theme="space")

    records = repo.load()
    assert len(records) == 3
    assert records[0]["score"] == 0.9
    assert records[-1]["score"] == 0.1
