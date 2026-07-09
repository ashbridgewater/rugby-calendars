"""Config loader (PyYAML) + validation."""
import pytest

from scripts.config_loader import load_config

_MINIMAL = """\
sources:
  a:
    enabled: true
    provider: aggregator
    source_url: "https://x.test/a/"
    tournament: autumn
    season: 2026
    cal_name: "A"
  b:
    enabled: false
    provider: aggregator
    source_url: "https://x.test/b/"
    tournament: summer
    season: 2026
    cal_name: "B"
derived:
  nations: {enabled: true, teams: [England]}
  all: {enabled: true, cal_name: "All"}
output: {calendar_dir: calendar, data_dir: data, state_dir: state}
metadata: {refresh_interval: PT12H, event_duration_minutes: 110, timezone: "Europe/London"}
"""


def test_loads_real_config():
    cfg = load_config("config/calendars.yml")
    assert len(cfg.sources) == 4
    assert len(cfg.enabled_sources()) == 4


def test_nations_and_all_flags():
    cfg = load_config("config/calendars.yml")
    assert cfg.nations_teams == ["England", "Scotland", "Wales", "Ireland"]
    assert cfg.all_enabled is True


def test_disabled_source_dropped_from_enabled(tmp_path):
    p = tmp_path / "c.yml"
    p.write_text(_MINIMAL, encoding="utf-8")
    cfg = load_config(p)
    assert len(cfg.sources) == 2
    assert [s.key for s in cfg.enabled_sources()] == ["a"]


def test_rejects_missing_source_url(tmp_path):
    p = tmp_path / "c.yml"
    p.write_text(_MINIMAL.replace('    source_url: "https://x.test/a/"\n', ""), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(p)
