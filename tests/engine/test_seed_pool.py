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
