"""End-to-end pipeline against saved HTML fixtures (offline)."""
import hashlib
import shutil
from pathlib import Path

from icalendar import Calendar

from scripts.run_pipeline import run as run_pipeline

CONFIG = "config/calendars.yml"


def _run(tmp_path, fixture_dir):
    return run_pipeline(
        CONFIG,
        fixture_dir=str(fixture_dir),
        data_dir=tmp_path / "data",
        calendar_dir=tmp_path / "cal",
        state_dir=tmp_path / "state",
    )


def _uids(path):
    cal = Calendar.from_ical(Path(path).read_text(encoding="utf-8"))
    return {str(e["UID"]) for e in cal.walk("VEVENT")}


def test_e2e_produces_nine_valid_calendars(tmp_path):
    assert _run(tmp_path, "tests/fixtures") == 0
    ics = sorted((tmp_path / "cal").glob("*.ics"))
    assert len(ics) == 9
    for p in ics:
        Calendar.from_ical(p.read_text(encoding="utf-8"))  # must parse


def test_e2e_all_ics_is_union_of_tournaments(tmp_path):
    _run(tmp_path, "tests/fixtures")
    caldir = tmp_path / "cal"
    union = set()
    for t in ("autumn_2026", "summer_2026", "six_nations_2027", "rwc_2027"):
        union |= _uids(caldir / f"{t}.ics")
    assert _uids(caldir / "all.ics") == union


def test_e2e_idempotent_byte_identical(tmp_path):
    _run(tmp_path, "tests/fixtures")
    h1 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "cal").glob("*.ics")}
    _run(tmp_path, "tests/fixtures")
    h2 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "cal").glob("*.ics")}
    assert h1 == h2


def test_e2e_empty_source_fails_and_preserves_prior(tmp_path):
    fdir = tmp_path / "fx"
    fdir.mkdir()
    for p in Path("tests/fixtures").glob("*_full.html"):
        shutil.copy(p, fdir / p.name)
    assert _run(tmp_path, fdir) == 0
    before = (tmp_path / "cal" / "autumn_2026.ics").read_bytes()

    (fdir / "six_nations_2027_full.html").write_text("<html><body></body></html>", encoding="utf-8")
    assert _run(tmp_path, fdir) != 0
    after = (tmp_path / "cal" / "autumn_2026.ics").read_bytes()
    assert before == after  # aborted before rebuild -> prior outputs untouched
