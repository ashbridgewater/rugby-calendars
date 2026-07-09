"""ICS builder: TZ, DTEND, STATUS, escaping, SEQUENCE, deterministic DTSTAMP."""
from datetime import date, datetime, timezone

from icalendar import Calendar

from scripts.build_ics import render_calendar, render_event
from scripts.providers.base import Fixture
from scripts.sequence_state import SequenceState

UTC = timezone.utc


def _fx(**kw):
    base = dict(
        tournament="summer", season=2026, stage="Round 2",
        home="New Zealand", away="Italy", venue="Hnry Stadium, Wellington",
        status="scheduled", source_url="https://x.test/",
        uid="summer-2026-round-2-new-zealand-v-italy@d",
        kickoff_utc=datetime(2026, 7, 11, 5, 10, tzinfo=UTC),
        date_local=date(2026, 7, 11),
    )
    base.update(kw)
    return Fixture(**base)


def _state(tmp_state_dir):
    return SequenceState(tmp_state_dir / "seq.json")


def test_summer_bst_dtstart(tmp_state_dir):
    assert "DTSTART:20260711T051000Z" in render_event(_fx(), _state(tmp_state_dir))


def test_dtend_is_start_plus_110(tmp_state_dir):
    assert "DTEND:20260711T070000Z" in render_event(_fx(), _state(tmp_state_dir))


def test_winter_gmt_dtstart(tmp_state_dir):
    ev = render_event(
        _fx(stage="Round 1", home="Ireland", away="England",
            uid="six-nations-2027-round-1-ireland-v-england@d",
            kickoff_utc=datetime(2027, 2, 5, 20, 10, tzinfo=UTC),
            date_local=date(2027, 2, 5)),
        _state(tmp_state_dir),
    )
    assert "DTSTART:20270205T201000Z" in ev


def test_tentative_status_and_placeholder_summary(tmp_state_dir):
    ev = render_event(
        _fx(status="tentative", home="Runner-up Pool C", away="Runner-up Pool F",
            home_placeholder=True, away_placeholder=True, uid="rwc-2027-R16-1@d",
            kickoff_utc=datetime(2027, 10, 23, 3, 15, tzinfo=UTC), date_local=date(2027, 10, 23)),
        _state(tmp_state_dir),
    )
    assert "STATUS:TENTATIVE" in ev
    assert "Runner-up Pool C" in ev


def test_scheduled_is_confirmed(tmp_state_dir):
    assert "STATUS:CONFIRMED" in render_event(_fx(), _state(tmp_state_dir))


def test_location_semicolon_escaped(tmp_state_dir):
    ev = render_event(_fx(venue="Aviva Stadium; Dublin"), _state(tmp_state_dir))
    assert "LOCATION:Aviva Stadium\\; Dublin" in ev


def test_sequence_increments_on_content_change(tmp_state_dir):
    st = _state(tmp_state_dir)
    render_event(_fx(), st)
    ev2 = render_event(_fx(venue="A Different Ground"), st)
    assert "SEQUENCE:1" in ev2


def test_dtstamp_deterministic_for_same_content(tmp_state_dir):
    assert render_event(_fx(), _state(tmp_state_dir)) == render_event(_fx(), _state(tmp_state_dir))


def test_played_all_day_when_no_prior(tmp_state_dir):
    ev = render_event(
        _fx(status="played", score="34-32", home="New Zealand", away="France",
            uid="summer-2026-round-1-new-zealand-v-france@d",
            kickoff_utc=None, date_local=date(2026, 7, 4)),
        _state(tmp_state_dir),
    )
    assert "DTSTART;VALUE=DATE:20260704" in ev
    assert "34-32" in ev


def test_played_carries_prior_kickoff(tmp_state_dir):
    st = _state(tmp_state_dir)
    render_event(_fx(uid="u-carry@d", kickoff_utc=datetime(2026, 7, 4, 5, 10, tzinfo=UTC)), st)
    ev = render_event(
        _fx(uid="u-carry@d", status="played", score="10-9", kickoff_utc=None, date_local=date(2026, 7, 4)),
        st,
    )
    assert "DTSTART:20260704T051000Z" in ev


def test_icalendar_round_trip(tmp_state_dir):
    cal = render_calendar(
        "Test", [_fx(), _fx(home="Fiji", away="Wales", uid="u2@d")], _state(tmp_state_dir)
    )
    parsed = Calendar.from_ical(cal)
    assert sum(1 for _ in parsed.walk("VEVENT")) == 2
