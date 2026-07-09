#!/usr/bin/env python3
"""End-to-end pipeline: scrape -> CSV -> build 9 ICS -> validate.

All-or-nothing: if any enabled source raises or yields zero fixtures, the run
aborts BEFORE writing anything, so the previously committed CSVs and ICS files
are preserved untouched. A ``--fixture-dir`` may be supplied to parse saved HTML
instead of hitting the network (used by tests and offline runs).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import scrape
from scripts.build_ics import build_all
from scripts.config_loader import load_config
from scripts.fixture_csv import write_csv
from scripts.providers.aggregator import AggregatorProvider
from scripts.validate_ics import validate_paths


def _fetch(src, fixture_dir, provider_for):
    if fixture_dir:
        html = (Path(fixture_dir) / f"{src.key}_full.html").read_text(encoding="utf-8")
        return AggregatorProvider().parse_html(html, src.tournament, src.season, src.source_url)
    provider = provider_for(src.provider)
    return provider.fetch(
        {"source_url": src.source_url, "tournament": src.tournament, "season": src.season}
    )


def run(config_path, *, fixture_dir=None, data_dir=None, calendar_dir=None,
        state_dir=None, provider_for=None) -> int:
    cfg = load_config(config_path)
    provider_for = provider_for or scrape._default_provider
    ddir = Path(data_dir) if data_dir else Path(cfg.data_dir)

    scraped: dict[str, list] = {}
    failed: list[str] = []
    for src in cfg.enabled_sources():
        try:
            fixtures = _fetch(src, fixture_dir, provider_for)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {src.key}: {exc}", file=sys.stderr)
            failed.append(src.key)
            continue
        if not fixtures:
            print(f"ERROR {src.key}: 0 fixtures scraped", file=sys.stderr)
            failed.append(src.key)
            continue
        scraped[src.key] = fixtures

    if failed:
        print(
            f"PIPELINE ABORTED: sources failed {failed}; prior outputs preserved",
            file=sys.stderr,
        )
        return 1

    for key, fixtures in scraped.items():
        write_csv(ddir / f"{key}.csv", fixtures)
        print(f"{key}: {len(fixtures)} fixtures")

    written = build_all(
        config_path, data_dir=ddir, calendar_dir=calendar_dir, state_dir=state_dir
    )
    if validate_paths(written) != 0:
        print("PIPELINE FAILED: invalid ICS output", file=sys.stderr)
        return 2

    print(f"PIPELINE OK: {len(written)} calendars written")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scrape + build + validate rugby calendars")
    ap.add_argument("--config", default="config/calendars.yml")
    ap.add_argument("--fixture-dir", default=None, help="parse saved HTML instead of HTTP")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--calendar-dir", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    return run(
        args.config,
        fixture_dir=args.fixture_dir,
        data_dir=args.data_dir,
        calendar_dir=args.calendar_dir,
        state_dir=args.state_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
