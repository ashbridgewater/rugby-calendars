"""Structural-slot UID stability."""
from scripts.uid import compute_uid, is_bracket_stage, slug, stage_code

DOMAIN = "@rugby-calendars.ashbridgewater.github.io"


def test_round_robin_uid_ignores_time_and_is_team_based():
    a = compute_uid("six_nations", 2027, "Round 1", "Ireland", "England", 1)
    b = compute_uid("six_nations", 2027, "Round 1", "Ireland", "England", 99)
    assert a == b  # slot ignored for round-robin
    assert "ireland-v-england" in a


def test_knockout_uid_stable_across_placeholder_resolution():
    placeholder = compute_uid("rwc", 2027, "Quarter Finals", "Winner R16 1", "Winner R16 3", 1)
    resolved = compute_uid("rwc", 2027, "Quarter Finals", "France", "Ireland", 1)
    assert placeholder == resolved  # slot-based, teams irrelevant
    assert placeholder.startswith("rwc-2027-QF-1")


def test_swap_home_away_changes_uid():
    a = compute_uid("six_nations", 2027, "Round 1", "England", "Wales", 1)
    b = compute_uid("six_nations", 2027, "Round 1", "Wales", "England", 1)
    assert a != b


def test_uid_ascii_and_domain_suffix():
    u = compute_uid("six_nations", 2027, "Round 1", "Ireland", "England", 1)
    assert u.isascii()
    assert u.endswith(DOMAIN)


def test_bracket_stage_detection():
    assert is_bracket_stage("Quarter Finals")
    assert is_bracket_stage("Round of 16")
    assert is_bracket_stage("Finals Weekend")
    assert is_bracket_stage("Bronze Final")
    assert not is_bracket_stage("Pool A")
    assert not is_bracket_stage("Round 1")
    assert not is_bracket_stage("Warm-up Matches")


def test_stage_codes():
    assert stage_code("Quarter Finals") == "QF"
    assert stage_code("Semi Finals") == "SF"
    assert stage_code("Bronze Final") == "BR"
    assert stage_code("Round of 16") == "R16"
    assert stage_code("Rugby World Cup Final") == "F"


def test_slug():
    assert slug("Six Nations 2027!") == "six-nations-2027"
