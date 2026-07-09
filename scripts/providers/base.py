"""Shared data model for all fixture providers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

# Fixture lifecycle status.
#   scheduled  -> future fixture with known teams
#   tentative  -> known slot but placeholder team(s) (e.g. RWC knockouts)
#   played     -> match already completed (score known, kickoff time may be gone)
_ALLOWED_STATUS = frozenset({"scheduled", "tentative", "played"})


@dataclass(frozen=True, slots=True)
class Fixture:
    """A single rugby fixture, normalised across every source."""

    tournament: str
    season: int
    stage: str  # "Round 1", "Pool A", "Quarter Finals", ...
    home: str
    away: str
    venue: str
    status: str
    source_url: str
    uid: str
    kickoff_utc: datetime | None = None
    date_local: date | None = None
    home_placeholder: bool = False
    away_placeholder: bool = False
    score: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_STATUS:
            raise ValueError(
                f"invalid status {self.status!r}; allowed: {sorted(_ALLOWED_STATUS)}"
            )
        if self.kickoff_utc is not None and self.kickoff_utc.tzinfo is None:
            raise ValueError("kickoff_utc must be timezone-aware (UTC)")

    def involves(self, team: str) -> bool:
        """True if `team` plays in this fixture (tolerant of 'England XV' etc.)."""
        needle = team.strip().lower()
        return (
            self.home.strip().lower().startswith(needle)
            or self.away.strip().lower().startswith(needle)
        )


@runtime_checkable
class Provider(Protocol):
    """A fixture source. Implementations fetch remote data and normalise it."""

    def fetch(self, source: dict) -> list[Fixture]:
        ...
