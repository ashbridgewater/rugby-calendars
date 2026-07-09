"""Stable, structural iCalendar UIDs.

Round-robin fixtures (pools, Six Nations rounds, tour matches) are keyed on the
teams, which never change -> ``{tournament}-{season}-{round}-{home}-v-{away}``.

Knockout / placement fixtures (RWC R16..Final, Nations Championship finals) are
keyed on their *bracket slot*, so a UID stays constant as "Winner Pool A"
resolves into a real team -> ``{tournament}-{season}-{stage_code}-{slot}``.
"""
from __future__ import annotations

import re

DOMAIN = "rugby-calendars.ashbridgewater.github.io"

_BRACKET_KEYWORDS = (
    "round of 16",
    "quarter",
    "semi",
    "bronze",
    "final",
    "playoff",
    "place",
)


def slug(value: str) -> str:
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    return v.strip("-")


def is_bracket_stage(stage: str) -> bool:
    """True for knockout / placement stages whose teams are positional."""
    s = stage.lower()
    return any(keyword in s for keyword in _BRACKET_KEYWORDS)


def stage_code(stage: str) -> str:
    s = stage.lower()
    if "quarter" in s:
        return "QF"
    if "semi" in s:
        return "SF"
    if "bronze" in s or "3rd place" in s or "third place" in s:
        return "BR"
    if "round of 16" in s or "r16" in s:
        return "R16"
    if "final" in s:
        return "F"
    return (slug(stage).upper().replace("-", "")) or "X"


def compute_uid(
    tournament: str,
    season: int,
    stage: str,
    home: str,
    away: str,
    slot: int,
) -> str:
    """Return the stable UID for a fixture."""
    if is_bracket_stage(stage):
        return f"{slug(tournament)}-{season}-{stage_code(stage)}-{slot}@{DOMAIN}"
    return (
        f"{slug(tournament)}-{season}-{slug(stage)}-"
        f"{slug(home)}-v-{slug(away)}@{DOMAIN}"
    )
