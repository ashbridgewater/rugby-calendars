#!/usr/bin/env python3
"""Build RFC5545 .ics calendars from the scraped per-tournament CSVs.

Produces, per run:
  * one .ics per enabled source (tournament feed)
  * one .ics per configured nation (its fixtures across every tournament)
  * all.ics (every fixture, de-duplicated by UID)

Correctness features:
  * kickoff datetimes are already UTC (see scripts/tz.py); emitted as ...Z
  * DTEND = DTSTART + event_duration_minutes
  * stable structural UIDs + SEQUENCE increments only on real content change
  * DTSTAMP is derived deterministically from event content, so unchanged
    fixtures produce byte-identical output (content-gated commits, no churn)
  * played matches keep the score in the SUMMARY; if their kickoff time is gone
    from the source they reuse a previously-recorded time, else become all-day
  * RFC5545 TEXT escaping + octet-safe line folding
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.config_loader import load_config
from scripts.fixture_csv import read_csv
from scripts.ics_utils import escape_text, fold_line
from scripts.providers.base import Fixture
from scripts.sequence_state import SequenceState

UTC = timezone.utc
_EPOCH = datetime(2020, 1, 1, tzinfo=UTC)
_DTSTAMP_WINDOW_SECONDS = 15 * 365 * 24 * 3600  # ~15 years of distinct values


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _summary(fx: Fixture) -> str:
    if fx.status == "played" and fx.score:
        return f"{fx.home} {fx.score} {fx.away}"
    return f"{fx.home} v {fx.away}"


def _status_ics(fx: Fixture) -> str:
    return "TENTATIVE" if fx.status == "tentative" else "CONFIRMED"


def _content_hash(fx: Fixture) -> str:
    """Hash of the *semantic* content (independent of any carried-forward time)."""
    own = fx.kickoff_utc.isoformat() if fx.kickoff_utc else ""
    payload = "|".join(
        [fx.uid, _summary(fx), _status_ics(fx), fx.venue, own, fx.score or "", fx.stage]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dtstamp(content_hash: str) -> str:
    secs = int(content_hash[:12], 16) % _DTSTAMP_WINDOW_SECONDS
    return (_EPOCH + timedelta(seconds=secs)).strftime("%Y%m%dT%H%M%SZ")


def _sort_key(fx: Fixture):
    if fx.kickoff_utc:
        return (_fmt_utc(fx.kickoff_utc), fx.uid)
    if fx.date_local:
        return (fx.date_local.strftime("%Y%m%dT000000Z"), fx.uid)
    return ("99999999T000000Z", fx.uid)


def render_event(fx: Fixture, state: SequenceState, *, duration_min: int = 110,
                 category: str = "Rugby") -> str:
    own_iso = fx.kickoff_utc.isoformat() if fx.kickoff_utc else None
    content_hash = _content_hash(fx)
    seq, prior = state.next_sequence(fx.uid, content_hash, own_iso)
    dtstamp = _dtstamp(content_hash)

    lines = ["BEGIN:VEVENT", f"UID:{fx.uid}", f"DTSTAMP:{dtstamp}"]

    start_dt = fx.kickoff_utc
    if start_dt is None and prior:
        try:
            start_dt = datetime.fromisoformat(prior)
        except ValueError:
            start_dt = None

    if start_dt is not None:
        lines.append(f"DTSTART:{_fmt_utc(start_dt)}")
        lines.append(f"DTEND:{_fmt_utc(start_dt + timedelta(minutes=duration_min))}")
    elif fx.date_local is not None:
        lines.append(f"DTSTART;VALUE=DATE:{fx.date_local.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{(fx.date_local + timedelta(days=1)).strftime('%Y%m%d')}")
    else:
        # No time or date at all (should not happen); anchor to epoch to stay valid.
        lines.append(f"DTSTART;VALUE=DATE:{_EPOCH.strftime('%Y%m%d')}")

    lines.append(f"SUMMARY:{escape_text(_summary(fx))}")
    if fx.venue:
        lines.append(f"LOCATION:{escape_text(fx.venue)}")
    lines.append(f"STATUS:{_status_ics(fx)}")
    lines.append(f"SEQUENCE:{seq}")
    lines.append(f"CATEGORIES:{escape_text(category)}")
    if fx.source_url:
        lines.append(f"URL:{fx.source_url}")

    desc = _summary(fx)
    if fx.venue:
        desc += f"\nVenue: {fx.venue}"
    if fx.status == "tentative":
        desc += "\n(Teams to be confirmed)"
    lines.append(f"DESCRIPTION:{escape_text(desc)}")
    lines.append("TRANSP:OPAQUE")
    lines.append("END:VEVENT")
    return "\r\n".join(fold_line(line) for line in lines)


def render_calendar(cal_name: str, fixtures, state: SequenceState, *,
                    tz: str = "Europe/London", refresh: str = "PT12H",
                    duration_min: int = 110, category: str = "Rugby",
                    caldesc: str | None = None) -> str:
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "PRODID:-//ashbridgewater//rugby-calendars//EN",
        f"X-WR-CALNAME:{escape_text(cal_name)}",
        f"X-WR-TIMEZONE:{tz}",
        f"X-WR-CALDESC:{escape_text(caldesc or cal_name)}",
        f"REFRESH-INTERVAL;VALUE=DURATION:{refresh}",
        f"X-PUBLISHED-TTL:{refresh}",
    ]
    parts = [fold_line(line) for line in header]
    for fx in fixtures:
        parts.append(render_event(fx, state, duration_min=duration_min, category=category))
    parts.append("END:VCALENDAR")
    return "\r\n".join(parts) + "\r\n"


def build_all(config_path, *, data_dir=None, calendar_dir=None, state_dir=None) -> list[Path]:
    cfg = load_config(config_path)
    ddir = Path(data_dir) if data_dir else Path(cfg.data_dir)
    cdir = Path(calendar_dir) if calendar_dir else Path(cfg.calendar_dir)
    sdir = Path(state_dir) if state_dir else Path(cfg.state_dir)
    cdir.mkdir(parents=True, exist_ok=True)

    state = SequenceState(sdir / "sequence.json")
    written: list[Path] = []
    all_fixtures: list[Fixture] = []

    common = dict(
        tz=cfg.timezone,
        refresh=cfg.refresh_interval,
        duration_min=cfg.event_duration_minutes,
    )

    # --- per-tournament feeds ---
    for src in cfg.enabled_sources():
        csv_path = ddir / f"{src.key}.csv"
        if not csv_path.exists():
            print(f"skip {src.key}: no CSV at {csv_path}", file=sys.stderr)
            continue
        fixtures = read_csv(csv_path)
        all_fixtures.extend(fixtures)
        text = render_calendar(
            src.cal_name, sorted(fixtures, key=_sort_key), state,
            category=f"Rugby,{src.cal_name}", caldesc=f"{src.cal_name} fixtures", **common,
        )
        out = cdir / f"{src.key}.ics"
        out.write_text(text, encoding="utf-8")
        written.append(out)

    # --- de-dupe combined pool for derived feeds ---
    dedup: dict[str, Fixture] = {}
    for fx in all_fixtures:
        dedup.setdefault(fx.uid, fx)
    combined = sorted(dedup.values(), key=_sort_key)

    # --- per-nation feeds ---
    if cfg.nations_enabled:
        for team in cfg.nations_teams:
            team_fx = [fx for fx in combined if fx.involves(team)]
            text = render_calendar(
                f"{team} Rugby Fixtures", team_fx, state,
                category=f"Rugby,{team}", caldesc=f"All {team} international fixtures", **common,
            )
            out = cdir / f"{team.lower()}.ics"
            out.write_text(text, encoding="utf-8")
            written.append(out)

    # --- all-in-one feed ---
    if cfg.all_enabled:
        text = render_calendar(
            cfg.all_cal_name, combined, state,
            category="Rugby", caldesc="Every international rugby fixture", **common,
        )
        out = cdir / "all.ics"
        out.write_text(text, encoding="utf-8")
        written.append(out)

    state.save()
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build .ics calendars from CSVs")
    ap.add_argument("--config", default="config/calendars.yml")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--calendar-dir", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    written = build_all(
        args.config, data_dir=args.data_dir, calendar_dir=args.calendar_dir, state_dir=args.state_dir
    )
    print(f"wrote {len(written)} calendars: {', '.join(p.name for p in written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
