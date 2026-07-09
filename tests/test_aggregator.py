"""Aggregator HTML provider — parses schema.org markup across all 4 sources."""
from datetime import datetime, timezone

from conftest import load_fixture
from scripts.providers.aggregator import AggregatorProvider

UTC = timezone.utc
AGG = AggregatorProvider()


# ---- snippet-level parsing --------------------------------------------------

def test_parses_future_fixture():
    fx = AGG.parse_html(load_fixture("snip_future.html"), "six_nations", 2027, "u")
    assert len(fx) == 1
    f = fx[0]
    assert f.home == "Ireland" and f.away == "England"
    assert f.status == "scheduled"
    assert f.kickoff_utc == datetime(2027, 2, 5, 20, 10, tzinfo=UTC)
    assert "Dublin" in f.venue


def test_parses_tbd_knockout():
    fx = AGG.parse_html(load_fixture("snip_tbd_knockout.html"), "rwc", 2027, "u")
    assert len(fx) == 1
    f = fx[0]
    assert f.status == "tentative"
    assert f.home_placeholder and f.away_placeholder
    assert f.home == "Runner-up Pool C"


def test_parses_past_result():
    fx = AGG.parse_html(load_fixture("snip_past_result.html"), "summer", 2026, "u")
    assert len(fx) == 1
    f = fx[0]
    assert f.status == "played"
    assert f.score == "35-19"
    assert f.home == "France XV"


# ---- full-page parsing (exact counts are regression guards) ------------------

def test_autumn_2026_full():
    fx = AGG.parse_html(load_fixture("autumn_2026_full.html"), "autumn", 2026, "u")
    assert len(fx) == 24
    assert all(f.home and f.away for f in fx)


def test_six_nations_2027_full():
    fx = AGG.parse_html(load_fixture("six_nations_2027_full.html"), "six_nations", 2027, "u")
    assert len(fx) == 15
    assert all(f.status == "scheduled" for f in fx)
    ie = next(f for f in fx if f.home == "Ireland" and f.away == "England")
    assert ie.kickoff_utc == datetime(2027, 2, 5, 20, 10, tzinfo=UTC)
    assert ie.stage.upper().startswith("ROUND 1")


def test_summer_2026_full_has_bst_and_played():
    fx = AGG.parse_html(load_fixture("summer_2026_full.html"), "summer", 2026, "u")
    assert len(fx) == 20
    assert any(f.status == "played" for f in fx)
    assert any(f.status == "scheduled" for f in fx)
    # BST correctness: 06:10 UK local (summer) -> 05:10 UTC
    nz = next(f for f in fx if f.home == "New Zealand" and f.away == "Italy")
    assert nz.kickoff_utc == datetime(2026, 7, 11, 5, 10, tzinfo=UTC)


def test_rwc_2027_full_has_tentative_and_scheduled():
    fx = AGG.parse_html(load_fixture("rwc_2027_full.html"), "rwc", 2027, "u")
    assert len(fx) == 52
    tentative = [f for f in fx if f.status == "tentative"]
    assert len(tentative) >= 16  # all knockout fixtures use placeholders
    # a real pool fixture is scheduled, not tentative
    ah = next(f for f in fx if f.home == "Australia" and f.away == "Hong Kong")
    assert ah.status == "scheduled"


def test_stage_inherited_from_heading():
    fx = AGG.parse_html(load_fixture("rwc_2027_full.html"), "rwc", 2027, "u")
    finals = [f for f in fx if "final" in f.stage.lower()]
    assert finals  # at least the RWC Final / Bronze Final / QF / SF captured
    assert all(f.uid.startswith("rwc-2027-") for f in fx)
