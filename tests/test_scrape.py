"""Scrape orchestrator: writes CSVs, fail-safe on empty/error."""
import csv

from scripts import scrape
from scripts.fixture_csv import FIELDS
from scripts.providers.base import Fixture
from datetime import datetime, timezone

UTC = timezone.utc

_CFG = """\
sources:
  a: {enabled: true, provider: aggregator, source_url: "http://x/a", tournament: autumn, season: 2026, cal_name: A}
  b: {enabled: false, provider: aggregator, source_url: "http://x/b", tournament: summer, season: 2026, cal_name: B}
derived: {nations: {enabled: true, teams: [England]}, all: {enabled: true}}
output: {calendar_dir: calendar, data_dir: data, state_dir: state}
metadata: {refresh_interval: PT12H, event_duration_minutes: 110, timezone: Europe/London}
"""


def _cfg(tmp_path):
    p = tmp_path / "c.yml"
    p.write_text(_CFG, encoding="utf-8")
    return p


def _fx(i):
    return Fixture(
        tournament="autumn", season=2026, stage="Round 4", home=f"Team{i}", away="Foe",
        venue="V", status="scheduled", source_url="http://x/a", uid=f"u{i}@d",
        kickoff_utc=datetime(2026, 11, 8, 15, 10, tzinfo=UTC),
    )


class _Mock:
    def __init__(self, fixtures=None, exc=False):
        self._f = fixtures or []
        self._e = exc

    def fetch(self, source):
        if self._e:
            raise RuntimeError("boom")
        return list(self._f)


def test_writes_csv_from_provider(tmp_path):
    rc = scrape.run(_cfg(tmp_path), provider_for=lambda n: _Mock([_fx(1), _fx(2), _fx(3)]), data_dir=tmp_path / "data")
    assert rc == 0
    rows = list(csv.DictReader(open(tmp_path / "data" / "a.csv", encoding="utf-8")))
    assert len(rows) == 3


def test_zero_fixtures_preserves_prior_csv(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.csv").write_text("uid\nkeep\n", encoding="utf-8")
    rc = scrape.run(_cfg(tmp_path), provider_for=lambda n: _Mock([]), data_dir=d)
    assert rc == 1
    assert (d / "a.csv").read_text(encoding="utf-8") == "uid\nkeep\n"


def test_exception_preserves_prior_csv(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.csv").write_text("uid\nkeep\n", encoding="utf-8")
    rc = scrape.run(_cfg(tmp_path), provider_for=lambda n: _Mock(exc=True), data_dir=d)
    assert rc == 1
    assert (d / "a.csv").read_text(encoding="utf-8") == "uid\nkeep\n"


def test_disabled_source_skipped(tmp_path):
    scrape.run(_cfg(tmp_path), provider_for=lambda n: _Mock([_fx(1)]), data_dir=tmp_path / "data")
    assert not (tmp_path / "data" / "b.csv").exists()


def test_csv_header_matches_fields(tmp_path):
    scrape.run(_cfg(tmp_path), provider_for=lambda n: _Mock([_fx(1)]), data_dir=tmp_path / "data")
    header = open(tmp_path / "data" / "a.csv", encoding="utf-8").readline().strip().split(",")
    assert header == FIELDS
