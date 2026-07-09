"""TZ conversion: the core correctness fix (BST vs GMT)."""
from datetime import datetime, timezone

from scripts.tz import parse_ko_content

UTC = timezone.utc


def test_summer_bst_naive_shifts_back_one_hour():
    # autumn-internationals.co.uk publishes naive UK wall-time; July = BST (UTC+1)
    assert parse_ko_content("2026-07-04T06:10") == datetime(2026, 7, 4, 5, 10, tzinfo=UTC)


def test_winter_gmt_naive_unchanged():
    # November = GMT = UTC
    assert parse_ko_content("2026-11-07T14:10") == datetime(2026, 11, 7, 14, 10, tzinfo=UTC)


def test_z_suffixed_treated_as_utc():
    # six-nations-guide.co.uk publishes Z-suffixed UTC with seconds
    assert parse_ko_content("2027-02-05T20:10:00Z") == datetime(2027, 2, 5, 20, 10, tzinfo=UTC)


def test_october_rwc_still_bst():
    # 1 Oct 2027 is before the last-Sunday-of-October switch -> BST
    assert parse_ko_content("2027-10-01T11:45") == datetime(2027, 10, 1, 10, 45, tzinfo=UTC)


def test_late_november_gmt():
    assert parse_ko_content("2027-11-13T09:00") == datetime(2027, 11, 13, 9, 0, tzinfo=UTC)


def test_result_always_utc_aware():
    r = parse_ko_content("2026-07-04T06:10")
    assert r.tzinfo == UTC
