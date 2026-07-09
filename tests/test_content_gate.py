"""Content-gated commits: unchanged inputs -> byte-identical outputs."""
import hashlib
from datetime import datetime, timezone

from scripts.build_ics import build_all
from scripts.fixture_csv import write_csv
from scripts.providers.base import Fixture

UTC = timezone.utc

_CFG = """\
sources:
  t: {enabled: true, provider: aggregator, source_url: "http://x/t", tournament: autumn, season: 2026, cal_name: T}
derived: {nations: {enabled: true, teams: [England]}, all: {enabled: true}}
output: {calendar_dir: calendar, data_dir: data, state_dir: state}
metadata: {refresh_interval: PT12H, event_duration_minutes: 110, timezone: Europe/London}
"""


def _digests(caldir):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(caldir.glob("*.ics"))}


def test_reruns_are_byte_identical(tmp_path):
    cfg = tmp_path / "c.yml"
    cfg.write_text(_CFG, encoding="utf-8")
    ddir = tmp_path / "data"
    write_csv(ddir / "t.csv", [
        Fixture(tournament="autumn", season=2026, stage="Round 4", home="England",
                away="Australia", venue="Twickenham", status="scheduled", source_url="u",
                uid="t-1@d", kickoff_utc=datetime(2026, 11, 8, 15, 10, tzinfo=UTC)),
    ])
    caldir = tmp_path / "cal"
    statedir = tmp_path / "state"
    build_all(cfg, data_dir=ddir, calendar_dir=caldir, state_dir=statedir)
    h1 = _digests(caldir)
    build_all(cfg, data_dir=ddir, calendar_dir=caldir, state_dir=statedir)
    h2 = _digests(caldir)
    assert h1 == h2
    assert len(h1) >= 3  # t.ics + england.ics + all.ics
