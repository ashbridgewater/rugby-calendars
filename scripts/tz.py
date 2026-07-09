"""Timezone handling: convert source kickoff strings to aware UTC datetimes.

This is the core correctness fix. Kickoffs on the source sites appear in two forms:

* ``2027-02-05T20:10:00Z``  -- offset-aware UTC (six-nations-guide.co.uk)
* ``2026-07-11T06:10``      -- naive UK wall-time (autumn-internationals.co.uk)

Naive values are interpreted as Europe/London and converted to UTC with full
DST awareness, so a 06:10 BST (summer) kickoff correctly becomes 05:10Z while a
14:10 GMT (winter) kickoff stays 14:10Z.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def parse_ko_content(iso: str) -> datetime:
    """Parse a schema.org ``startDate`` content value into an aware UTC datetime."""
    dt = datetime.fromisoformat(iso.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LONDON)
    return dt.astimezone(timezone.utc)
