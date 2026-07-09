"""Aggregator HTML provider.

Parses the shared schema.org markup used by autumn-internationals.co.uk and
six-nations-guide.co.uk. Handles three fixture shapes:

  * div.match-link  -> future fixture (has span.ko[content]) or past result
                       (has span.attendance, title carries the score)
  * div.match       -> fixture without a detail page (real teams OR knockout
                       placeholders such as "Winner Pool A")

Teams come from ``img.home`` / ``img.away`` alt text; kickoff from the
machine-readable ``span.ko[content]`` ISO value; stage/date from the preceding
``h3.round-heading`` / ``p.date-heading``.
"""
from __future__ import annotations

import re
from datetime import date

import requests
from bs4 import BeautifulSoup

from scripts import uid as uidmod
from scripts.providers.base import Fixture
from scripts.tz import parse_ko_content

HEADERS = {
    "User-Agent": (
        "rugby-calendars-bot/2.0 "
        "(+https://github.com/ashbridgewater/rugby-calendars)"
    )
}

_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ],
        start=1,
    )
}
_DATE_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})")
_SCORE_RE = re.compile(r"(\d{1,3})\s*[-\u2013]\s*(\d{1,3})")
_PLACEHOLDER_PREFIXES = (
    "winner", "runner-up", "runner up", "best ", "loser",
    "1st place", "2nd place", "3rd place", "4th place", "5th place", "6th place",
)


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _is_placeholder(name: str) -> bool:
    n = name.strip().lower()
    return any(n.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)


def _parse_date(text: str) -> date | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    day, month_name, year = m.groups()
    month = _MONTHS.get(month_name.lower())
    if not month:
        return None
    return date(int(year), month, int(day))


class AggregatorProvider:
    def fetch(self, source: dict) -> list[Fixture]:
        resp = requests.get(source["source_url"], headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return self.parse_html(
            resp.text,
            source["tournament"],
            int(source["season"]),
            source["source_url"],
        )

    def parse_html(
        self,
        html: str,
        tournament: str,
        season: int,
        source_url: str,
    ) -> list[Fixture]:
        soup = BeautifulSoup(html, "lxml")
        current_stage = ""
        current_date: date | None = None
        slot_counts: dict[str, int] = {}
        fixtures: list[Fixture] = []

        for el in soup.select(
            "h3.round-heading, p.date-heading, div.match-link, div.match"
        ):
            classes = el.get("class", [])
            if "round-heading" in classes:
                current_stage = _clean(el.get_text())
                continue
            if "date-heading" in classes:
                current_date = _parse_date(el.get_text())
                continue
            fx = self._parse_match(
                el, current_stage, current_date, tournament, season,
                source_url, slot_counts,
            )
            if fx is not None:
                fixtures.append(fx)
        return fixtures

    def _parse_match(
        self, el, stage, date_local, tournament, season, source_url, slot_counts
    ) -> Fixture | None:
        home_img = el.select_one("img.home")
        away_img = el.select_one("img.away")
        if home_img is None or away_img is None:
            return None
        home = _clean(home_img.get("alt", ""))
        away = _clean(away_img.get("alt", ""))
        if not home or not away:
            return None

        venue_span = el.select_one("span.venue")
        venue = _clean(venue_span.get_text()) if venue_span else ""

        title_span = el.select_one("span.title")
        title = _clean(title_span.get_text()) if title_span else f"{home} v {away}"

        ko = el.select_one("span.ko")
        ko_content = ko.get("content") if ko is not None else None
        attendance = el.select_one("span.attendance")

        home_ph = _is_placeholder(home)
        away_ph = _is_placeholder(away)

        slot = 0
        if uidmod.is_bracket_stage(stage):
            slot_counts[stage] = slot_counts.get(stage, 0) + 1
            slot = slot_counts[stage]
        uid = uidmod.compute_uid(tournament, season, stage, home, away, slot)

        kickoff_utc = None
        score = None
        if attendance is not None and not ko_content:
            status = "played"
            m = _SCORE_RE.search(title)
            if m:
                score = f"{m.group(1)}-{m.group(2)}"
        else:
            if ko_content:
                kickoff_utc = parse_ko_content(ko_content)
            status = "tentative" if (home_ph or away_ph) else "scheduled"

        return Fixture(
            tournament=tournament,
            season=season,
            stage=stage,
            home=home,
            away=away,
            venue=venue,
            status=status,
            source_url=source_url,
            uid=uid,
            kickoff_utc=kickoff_utc,
            date_local=date_local,
            home_placeholder=home_ph,
            away_placeholder=away_ph,
            score=score,
        )
