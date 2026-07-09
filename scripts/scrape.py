#!/usr/bin/env python3
"""Scrape enabled sources into per-tournament CSVs.

Fail-safe: if a source raises or yields zero fixtures, its existing CSV is left
untouched and the run reports failure (non-zero exit) so a bad scrape never
overwrites good committed data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.config_loader import load_config
from scripts.fixture_csv import write_csv
from scripts.providers.aggregator import AggregatorProvider

_PROVIDERS = {"aggregator": AggregatorProvider}


def _default_provider(name: str):
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"unknown provider: {name!r}")
    return cls()


def run(config_path, *, provider_for=None, data_dir=None, dry_run: bool = False) -> int:
    cfg = load_config(config_path)
    provider_for = provider_for or _default_provider
    ddir = Path(data_dir) if data_dir else Path(cfg.data_dir)

    failures: list[str] = []
    for src in cfg.enabled_sources():
        if dry_run:
            print(f"would scrape {src.key} <- {src.source_url}")
            continue
        try:
            provider = provider_for(src.provider)
            fixtures = provider.fetch(
                {"source_url": src.source_url, "tournament": src.tournament, "season": src.season}
            )
        except Exception as exc:  # noqa: BLE001 - any provider failure is a soft failure
            print(f"ERROR {src.key}: {exc}", file=sys.stderr)
            failures.append(src.key)
            continue
        if not fixtures:
            print(f"WARNING {src.key}: 0 fixtures scraped; preserving existing CSV", file=sys.stderr)
            failures.append(src.key)
            continue
        write_csv(ddir / f"{src.key}.csv", fixtures)
        print(f"{src.key}: wrote {len(fixtures)} fixtures -> {ddir / (src.key + '.csv')}")

    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scrape rugby fixtures into CSVs")
    ap.add_argument("--config", default="config/calendars.yml")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    return run(args.config, data_dir=args.data_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
