import pytest

from analytics.taste_model import compute_taste, taste_extremes
from config.settings import TASTE_MAX, TASTE_MIN


def _entry(rating=None, **dna):
    entry = {"dna": dna}
    if rating is not None:
        entry["rating"] = rating
    return entry


def test_empty_history_gives_empty_taste():
    assert compute_taste([]) == {}


def test_unrated_entries_are_ignored():
    assert compute_taste([_entry(mood="eerie"), _entry(mood="eerie")]) == {}


def test_one_like_is_a_gentle_boost():
    taste = compute_taste([_entry(1, mood="eerie")])

    assert taste["mood"]["eerie"] == pytest.approx(1.25)


def test_four_likes_boost_more_but_stay_below_the_cap():
    taste = compute_taste([_entry(1, mood="eerie")] * 4)

    assert taste["mood"]["eerie"] == pytest.approx(1 + 4 / 7)
    assert taste["mood"]["eerie"] < TASTE_MAX


def test_one_dislike_is_a_gentle_penalty():
    taste = compute_taste([_entry(-1, mood="serene")])

    assert taste["mood"]["serene"] == pytest.approx(0.75)


def test_many_dislikes_floor_at_taste_min_never_zero():
    taste = compute_taste([_entry(-1, mood="serene")] * 50)

    assert taste["mood"]["serene"] == TASTE_MIN
    assert TASTE_MIN > 0


def test_many_likes_never_exceed_taste_max():
    taste = compute_taste([_entry(1, mood="eerie")] * 1000)

    assert taste["mood"]["eerie"] <= TASTE_MAX


def test_equal_likes_and_dislikes_net_to_neutral():
    taste = compute_taste([_entry(1, mood="eerie"), _entry(-1, mood="eerie")])

    assert taste["mood"]["eerie"] == pytest.approx(1.0)


def test_each_trait_value_is_scored_independently():
    taste = compute_taste([
        _entry(1, mood="eerie", light_time="golden hour"),
        _entry(-1, mood="serene", light_time="golden hour"),
    ])

    assert taste["mood"]["eerie"] == pytest.approx(1.25)
    assert taste["mood"]["serene"] == pytest.approx(0.75)
    assert taste["light_time"]["golden hour"] == pytest.approx(1.0)


VALID = {"dna": {"mood": "eerie"}, "rating": 1}  # contributes exactly {"mood": {"eerie": 1.25}}


def _only_valid_counts(*bad_records):
    taste = compute_taste([*bad_records, VALID])
    assert taste == {"mood": {"eerie": pytest.approx(1.25)}}


def test_non_dict_records_are_ignored():
    _only_valid_counts(None, 5, "text", [1, 2], ("dna", "rating"))


def test_non_dict_dna_is_ignored():
    _only_valid_counts(
        {"dna": None, "rating": 1},
        {"dna": "eerie", "rating": 1},
        {"dna": ["mood", "eerie"], "rating": 1},
        {"dna": 7, "rating": 1},
        {"rating": 1},
    )


def test_non_string_trait_names_and_values_are_ignored():
    _only_valid_counts(
        {"dna": {1: "eerie", None: "eerie", ("a",): "eerie"}, "rating": 1},
        {"dna": {"mood": None, "lens": 3, "framing": ["wide"], "camera_angle": {"x": 1}}, "rating": 1},
        {"dna": {"scene_density_score": 7}, "rating": 1},
    )


@pytest.mark.parametrize("bad", [0, 2, -2, True, False, 1.0, -1.0, "1", "like", None, [1], {"v": 1}])
def test_invalid_ratings_are_ignored(bad):
    _only_valid_counts({"dna": {"mood": "eerie"}, "rating": bad})


def test_non_list_history_gives_empty_taste():
    assert compute_taste(None) == {}
    assert compute_taste("history") == {}
    assert compute_taste({"rating": 1}) == {}


def test_taste_extremes_orders_and_limits():
    taste = {
        "mood": {"a": 1.5, "b": 1.25, "c": 1.1, "d": 1.05, "e": 0.75, "f": 0.5},
        "lens": {"g": 1.0},
    }

    boosted, penalized = taste_extremes(taste, n=3)

    assert boosted == [("mood", "a", 1.5), ("mood", "b", 1.25), ("mood", "c", 1.1)]
    assert penalized == [("mood", "f", 0.5), ("mood", "e", 0.75)]


def test_taste_extremes_of_empty_taste():
    assert taste_extremes({}) == ([], [])
