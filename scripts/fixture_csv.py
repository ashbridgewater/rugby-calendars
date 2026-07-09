"""Serialise Fixture <-> CSV. The CSV is the human-editable override layer."""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from scripts.providers.base import Fixture

FIELDS = [
    "uid",
    "tournament",
    "season",
    "stage",
    "home",
    "away",
    "home_placeholder",
    "away_placeholder",
    "venue",
    "kickoff_utc",
    "date_local",
    "status",
    "score",
    "source_url",
]


def to_row(f: Fixture) -> dict:
    return {
        "uid": f.uid,
        "tournament": f.tournament,
        "season": str(f.season),
        "stage": f.stage,
        "home": f.home,
        "away": f.away,
        "home_placeholder": "1" if f.home_placeholder else "0",
        "away_placeholder": "1" if f.away_placeholder else "0",
        "venue": f.venue,
        "kickoff_utc": f.kickoff_utc.isoformat() if f.kickoff_utc else "",
        "date_local": f.date_local.isoformat() if f.date_local else "",
        "status": f.status,
        "score": f.score or "",
        "source_url": f.source_url,
    }


def from_row(row: dict) -> Fixture:
    ku = (row.get("kickoff_utc") or "").strip()
    dl = (row.get("date_local") or "").strip()
    return Fixture(
        tournament=row["tournament"],
        season=int(row["season"]),
        stage=row["stage"],
        home=row["home"],
        away=row["away"],
        venue=row.get("venue", ""),
        status=row["status"],
        source_url=row.get("source_url", ""),
        uid=row["uid"],
        kickoff_utc=datetime.fromisoformat(ku) if ku else None,
        date_local=date.fromisoformat(dl) if dl else None,
        home_placeholder=row.get("home_placeholder") == "1",
        away_placeholder=row.get("away_placeholder") == "1",
        score=(row.get("score") or None),
    )


def write_csv(path, fixtures) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for fx in fixtures:
            writer.writerow(to_row(fx))


def read_csv(path) -> list[Fixture]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return [from_row(r) for r in csv.DictReader(fh)]
