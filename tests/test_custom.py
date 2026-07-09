"""Custom composite feeds: union of whole tournaments + specific teams."""
from datetime import datetime, timezone

from icalendar import Calendar

from scripts.build_ics import build_all
from scripts.fixture_csv import write_csv
from scripts.providers.base import Fixture

UTC = timezone.utc

_CFG = """\
sources:
  sn: {enabled: true, provider: aggregator, source_url: "http://x/sn", tournament: six_nations, season: 2027, cal_name: "Six Nations 2027"}
  au: {enabled: true, provider: aggregator, source_url: "http://x/au", tournament: autumn, season: 2026, cal_name: "Autumn 2026"}
derived:
  nations: {enabled: false, teams: []}
  all: {enabled: false}
  custom:
    sn_plus_eng:
      enabled: true
      cal_name: "Six Nations + England (all competitions)"
      include_tournaments: [six_nations]
      include_teams: [England]
output: {calendar_dir: calendar, data_dir: data, state_dir: state}
metadata: {refresh_interval: PT12H, event_duration_minutes: 120, timezone: Europe/London}
"""


def _fx(uid, tournament, home, away, day):
    return Fixture(
        tournament=tournament, season=2027, stage="Round 1", home=home, away=away,
        venue="V", status="scheduled", source_url="u", uid=uid,
        kickoff_utc=datetime(2027, 2, day, 15, 0, tzinfo=UTC),
    )


def _summaries(path):
    cal = Calendar.from_ical(path.read_text(encoding="utf-8"))
    return sorted(str(e["SUMMARY"]) for e in cal.walk("VEVENT"))


def test_custom_feed_is_tournament_plus_team_union(tmp_path):
    cfg = tmp_path / "c.yml"
    cfg.write_text(_CFG, encoding="utf-8")
    ddir = tmp_path / "data"
    write_csv(ddir / "sn.csv", [
        _fx("sn-eng", "six_nations", "England", "Wales", 6),
        _fx("sn-fra", "six_nations", "France", "Italy", 7),
    ])
    write_csv(ddir / "au.csv", [
        _fx("au-eng", "autumn", "England", "Australia", 8),      # England outside SN -> in
        _fx("au-sco", "autumn", "Scotland", "New Zealand", 9),   # neither -> out
    ])
    build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    assert _summaries(tmp_path / "cal" / "sn_plus_eng.ics") == [
        "England v Australia", "England v Wales", "France v Italy",
    ]


def test_custom_feed_dedupes_team_games_within_included_tournament(tmp_path):
    cfg = tmp_path / "c.yml"
    cfg.write_text(_CFG, encoding="utf-8")
    ddir = tmp_path / "data"
    write_csv(ddir / "sn.csv", [_fx("sn-eng", "six_nations", "England", "Wales", 6)])
    build_all(cfg, data_dir=ddir, calendar_dir=tmp_path / "cal", state_dir=tmp_path / "state")
    # England v Wales matches BOTH rules but must appear exactly once
    assert _summaries(tmp_path / "cal" / "sn_plus_eng.ics") == ["England v Wales"]
