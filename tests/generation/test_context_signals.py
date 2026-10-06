from datetime import datetime

import pytest

from generation.context_signals import get_context, get_season, get_time_of_day


@pytest.mark.parametrize("hour,expected", [
    (0, "night"), (4, "night"), (5, "morning"), (11, "morning"),
    (12, "afternoon"), (16, "afternoon"), (17, "evening"), (20, "evening"),
    (21, "night"), (23, "night"),
])
def test_time_of_day_boundaries(hour, expected):
    assert get_time_of_day(datetime(2026, 6, 15, hour, 30)) == expected


@pytest.mark.parametrize("month,expected", [
    (12, "winter"), (1, "winter"), (2, "winter"),
    (3, "spring"), (5, "spring"),
    (6, "summer"), (8, "summer"),
    (9, "autumn"), (11, "autumn"),
])
def test_season_boundaries(month, expected):
    assert get_season(datetime(2026, month, 15, 12)) == expected


def test_get_context_combines_both_signals():
    assert get_context(datetime(2026, 12, 25, 22)) == {"time_of_day": "night", "season": "winter"}


def test_signals_default_to_the_system_clock():
    assert get_time_of_day() in {"morning", "afternoon", "evening", "night"}
    assert get_season() in {"winter", "spring", "summer", "autumn"}
