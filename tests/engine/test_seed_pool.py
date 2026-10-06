from config.settings import BEST_SEED_MUTATION_RANGE
from database.seeds import SeedRepository
from engine.seed_pool import SeedPool


def _record(seed, score=0.9, generation=0, parent_seed=None):
    return {
        "seed": seed,
        "score": score,
        "sampler_index": 0,
        "prompt": "p",
        "theme": "t",
        "parent_seed": parent_seed,
        "generation": generation,
    }


def test_next_seed_fresh_returns_seed_none_zero(tmp_path):
    pool = SeedPool(SeedRepository(tmp_path / "seeds.json"))

    seed, parent_seed, generation = pool.next_seed()

    assert isinstance(seed, int)
    assert parent_seed is None
    assert generation == 0


def test_next_seed_reuse_mutates_within_range_and_tracks_lineage(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(1_000_000, generation=2)])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)  # always reuse

    for _ in range(50):
        seed, parent_seed, generation = pool.next_seed()
        assert abs(seed - 1_000_000) <= BEST_SEED_MUTATION_RANGE
        assert parent_seed == 1_000_000
        assert generation == 3


def test_next_seed_clamps_mutated_seed_to_valid_range(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(10)])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)
    monkeypatch.setattr("engine.seed_pool.random.randint", lambda a, b: -BEST_SEED_MUTATION_RANGE)

    seed, parent_seed, _ = pool.next_seed()
    assert seed == 0
    assert parent_seed == 10

    repo.save([_record(2**63 - 1)])
    monkeypatch.setattr("engine.seed_pool.random.randint", lambda a, b: BEST_SEED_MUTATION_RANGE)
    seed, _, _ = pool.next_seed()
    assert seed == 2**63 - 1


def test_next_seed_tolerates_legacy_records_without_lineage_fields(tmp_path, monkeypatch):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([{"seed": 5000, "score": 0.9, "sampler_index": 0, "prompt": "p", "theme": "t"}])
    pool = SeedPool(repo)
    monkeypatch.setattr("engine.seed_pool.random.random", lambda: 0.0)

    seed, parent_seed, generation = pool.next_seed()

    assert parent_seed == 5000
    assert generation == 1


def test_record_result_persists_ranked_by_score(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111, 222], score=0.9, prompt="a cat", theme="fantasy")
    pool.record_result(seeds=[333], score=0.1, prompt="a dog", theme="space")

    records = repo.load()
    assert len(records) == 3
    assert records[0]["score"] == 0.9
    assert records[-1]["score"] == 0.1


def test_record_result_defaults_lineage_when_omitted(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(seeds=[111], score=0.5, prompt="p", theme="t")

    record = repo.load()[0]
    assert record["parent_seed"] is None
    assert record["generation"] == 0


def test_record_result_stores_lineage_per_seed(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    pool = SeedPool(repo)

    pool.record_result(
        seeds=[111, 222], score=0.5, prompt="p", theme="t",
        lineage=[(None, 0), (99, 3)],
    )

    by_seed = {r["seed"]: r for r in repo.load()}
    assert by_seed[111]["parent_seed"] is None
    assert by_seed[111]["generation"] == 0
    assert by_seed[222]["parent_seed"] == 99
    assert by_seed[222]["generation"] == 3


import threading

from config.settings import SEED_RATING_DISLIKE_MULTIPLIER, SEED_RATING_LIKE_MULTIPLIER


def _seeded_pool(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(1, score=0.5), _record(2, score=0.4), _record(3, score=0.3)])
    return repo, SeedPool(repo)


def test_rate_current_like_multiplies_only_matching_seeds(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.rate_current([1, 2], liked=True)

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[1] == 0.5 * SEED_RATING_LIKE_MULTIPLIER
    assert scores[2] == 0.4 * SEED_RATING_LIKE_MULTIPLIER
    assert scores[3] == 0.3


def test_rate_current_dislike_uses_dislike_multiplier(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.rate_current([3], liked=False)

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[3] == 0.3 * SEED_RATING_DISLIKE_MULTIPLIER
    assert scores[1] == 0.5


def test_rate_current_with_unknown_seed_leaves_records_unchanged(tmp_path):
    repo, pool = _seeded_pool(tmp_path)
    before = repo.load()

    pool.rate_current([999], liked=True)

    assert repo.load() == before


def test_penalize_zeroes_matching_seeds_only(tmp_path):
    repo, pool = _seeded_pool(tmp_path)

    pool.penalize([1])

    scores = {r["seed"]: r["score"] for r in repo.load()}
    assert scores[1] == 0.0
    assert scores[2] == 0.4


def test_concurrent_record_and_rate_do_not_lose_updates(tmp_path):
    repo = SeedRepository(tmp_path / "seeds.json")
    repo.save([_record(0, score=0.5)])
    pool = SeedPool(repo)

    def record(i):
        pool.record_result(seeds=[i], score=0.1, prompt="p", theme="t")

    def rate():
        for _ in range(20):
            pool.rate_current([0], liked=True)

    threads = [threading.Thread(target=record, args=(i,)) for i in range(1, 21)]
    threads.append(threading.Thread(target=rate))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert {r["seed"] for r in repo.load()} == set(range(0, 21))
