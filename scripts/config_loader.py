"""Load and validate config/calendars.yml (PyYAML-backed)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_REQUIRED_SOURCE_KEYS = ("provider", "source_url", "tournament", "season")


@dataclass(frozen=True)
class SourceCfg:
    key: str
    enabled: bool
    provider: str
    source_url: str
    tournament: str
    season: int
    cal_name: str


@dataclass(frozen=True)
class Config:
    sources: dict[str, SourceCfg]
    nations_enabled: bool
    nations_teams: list[str]
    all_enabled: bool
    all_cal_name: str
    calendar_dir: str
    data_dir: str
    state_dir: str
    refresh_interval: str
    event_duration_minutes: int
    timezone: str

    def enabled_sources(self) -> list[SourceCfg]:
        return [s for s in self.sources.values() if s.enabled]


def load_config(path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")

    raw_sources = data.get("sources") or {}
    if not raw_sources:
        raise ValueError("config has no 'sources'")

    sources: dict[str, SourceCfg] = {}
    for key, s in raw_sources.items():
        if not isinstance(s, dict):
            raise ValueError(f"source {key!r} must be a mapping")
        for req in _REQUIRED_SOURCE_KEYS:
            if s.get(req) in (None, ""):
                raise ValueError(f"source {key!r} missing required field {req!r}")
        sources[key] = SourceCfg(
            key=key,
            enabled=bool(s.get("enabled", True)),
            provider=str(s["provider"]),
            source_url=str(s["source_url"]),
            tournament=str(s["tournament"]),
            season=int(s["season"]),
            cal_name=str(s.get("cal_name", key)),
        )

    derived = data.get("derived") or {}
    nations = derived.get("nations") or {}
    all_cfg = derived.get("all") or {}
    output = data.get("output") or {}
    meta = data.get("metadata") or {}

    return Config(
        sources=sources,
        nations_enabled=bool(nations.get("enabled", False)),
        nations_teams=list(nations.get("teams") or []),
        all_enabled=bool(all_cfg.get("enabled", False)),
        all_cal_name=str(all_cfg.get("cal_name", "All Fixtures")),
        calendar_dir=str(output.get("calendar_dir", "calendar")),
        data_dir=str(output.get("data_dir", "data")),
        state_dir=str(output.get("state_dir", "state")),
        refresh_interval=str(meta.get("refresh_interval", "PT12H")),
        event_duration_minutes=int(meta.get("event_duration_minutes", 120)),
        timezone=str(meta.get("timezone", "Europe/London")),
    )
