#!/usr/bin/env python3
"""Validate generated .ics files before they are committed.

Checks each file parses via the ``icalendar`` library, contains at least one
VEVENT, that every VEVENT has UID/DTSTART/SUMMARY, and that no physical line
exceeds 75 octets (i.e. folding worked).
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from icalendar import Calendar

_MAX_OCTETS = 75
_REQUIRED = ("UID", "DTSTART", "SUMMARY")


def validate_file(path) -> list[str]:
    p = Path(path)
    errors: list[str] = []
    text = p.read_text(encoding="utf-8")

    # splitlines() copes with \r\n, \n or \r (read_text applies universal newlines,
    # so committed CRLF calendars arrive here as \n-delimited physical lines).
    for lineno, line in enumerate(text.splitlines(), start=1):
        if len(line.encode("utf-8")) > _MAX_OCTETS:
            errors.append(f"{p.name}:{lineno}: line exceeds {_MAX_OCTETS} octets")

    try:
        cal = Calendar.from_ical(text)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{p.name}: parse error: {exc}")
        return errors

    vevents = list(cal.walk("VEVENT"))
    if not vevents:
        errors.append(f"{p.name}: no VEVENT found")
    for ev in vevents:
        for req in _REQUIRED:
            if ev.get(req) is None:
                errors.append(f"{p.name}: a VEVENT is missing {req}")
                break
    return errors


def validate_paths(paths) -> int:
    paths = list(paths)
    errors: list[str] = []
    for path in paths:
        errors.extend(validate_file(path))
    for err in errors:
        print(err, file=sys.stderr)
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"validation ok: {len(paths)} file(s)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate .ics files")
    ap.add_argument("paths", nargs="+", help="ICS files or globs")
    args = ap.parse_args(argv)
    expanded: list[str] = []
    for pattern in args.paths:
        matched = glob.glob(pattern)
        expanded.extend(matched if matched else [pattern])
    if not expanded:
        print("no files matched", file=sys.stderr)
        return 1
    return validate_paths(expanded)


if __name__ == "__main__":
    sys.exit(main())
