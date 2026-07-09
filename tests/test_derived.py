"""Derived calendars: per-nation filtering + all.ics dedup."""
from datetime import datetime, timezone

from icalendar import Calendar

from scripts.build_ics import build_all
from scripts.fixture_csv import write_csv
from scripts.providers.base import Fixture

UTC = timezone.utc

_CFG = """\
sources:
  sn: {enabled: true, provider: aggregator, source_url: "http://x/sn", tournament: six_nations, season: 2027, cal_name: "Six Nations 2027"}
derived:
  nations: {enabled: true, teams: [England, Scotland, Wales, Ireland]}
  all: {enabled: true, cal_name: "All Fixtures"}
output: {calendar_dir: calendar, data_dir: data, state_dir: state}
metadata: {refresh_interval: PT12H, event_duration_minutes: 110, timezone: Europe/London}
"""


def _fx(uid, home, away, when):
    return Fixture(
        tournament="six_nations", season=2027, stage="Round 1", home=home, away=away,
        venue="V", status="scheduled", source_url="u", uid=uid, kickoff_utc=when,
    )


def _setup(tmp_path):
    cfg = tmp_path / "c.yml"
    cfg.write_text(_CFG, encoding="utf-8")
    ddir = tmp_path / "data"
    write_csv(ddir / "sn.csv", [
        _fx("sn-1", "England", "Wales", datetime(2027, 2, 1, 15, 0, tzinfo=UTC)),
        _fx("sn-2", "France", "Italy", datetime(2027, 2, 2, 15, 0, tzinfo=UTC)),
        _fx("sn-3", "Scotland", "England", datetime(2027, 2, 3, 15, 0, tzinfo=UTC)),
    ])
    return cfg, ddir


def _count(path):
    return sum(1 for _ in Calendar.from_ical(path.read_text(encoding="utf-8")).walk("VEVENT"))


def test_build_all_writes_expected_files(tmp_path):
    cfg, ddir = _setup(tmp_path)
    written = build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    names = {p.name for p in written}
    assert {"sn.ics", "england.ics", "scotland.ics", "wales.ics", "ireland.ics", "all.ics"} <= names


def test_england_feed_contains_only_england(tmp_path):
    cfg, ddir = _setup(tmp_path)
    build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    cal = Calendar.from_ical((tmp_path / "cal" / "england.ics").read_text(encoding="utf-8"))
    evs = list(cal.walk("VEVENT"))
    assert len(evs) == 2  # England v Wales + Scotland v England
    assert all("England" in str(e["SUMMARY"]) for e in evs)


def test_all_ics_count_equals_unique(tmp_path):
    cfg, ddir = _setup(tmp_path)
    build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    assert _count(tmp_path / "cal" / "all.ics") == 3
    assert _count(tmp_path / "cal" / "sn.ics") == 3


def test_all_ics_sorted_by_dtstart(tmp_path):
    cfg, ddir = _setup(tmp_path)
    build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    cal = Calendar.from_ical((tmp_path / "cal" / "all.ics").read_text(encoding="utf-8"))
    starts = [e["DTSTART"].dt for e in cal.walk("VEVENT")]
    assert starts == sorted(starts)
