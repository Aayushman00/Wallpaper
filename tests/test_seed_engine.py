from core.seed_engine import SeedEngine
from database.seeds import SeedRepository

def test_seed_is_integer(tmp_path):

    repo = SeedRepository(
        tmp_path / "seeds.json"
    )

    engine = SeedEngine(repo)

    seed = engine.get_seed()

    assert isinstance(seed, int)