"""Time-of-day and season signals used to nudge prompt generation."""

from __future__ import annotations

from datetime import datetime


def get_time_of_day(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def get_season(now: datetime | None = None) -> str:
    # ponytail: Northern Hemisphere only, add a hemisphere setting if that ever matters
    month = (now or datetime.now()).month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def get_context(now: datetime | None = None) -> dict[str, str]:
    now = now or datetime.now()
    return {"time_of_day": get_time_of_day(now), "season": get_season(now)}
