"""icalendar validation gate."""
from scripts.validate_ics import validate_file, validate_paths

_VALID = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//x//EN",
    "BEGIN:VEVENT", "UID:u@d", "DTSTAMP:20200101T000000Z",
    "DTSTART:20270205T201000Z", "SUMMARY:Ireland v England",
    "END:VEVENT", "END:VCALENDAR",
]) + "\r\n"


def test_valid_file_has_no_errors(tmp_path):
    p = tmp_path / "ok.ics"
    p.write_text(_VALID, encoding="utf-8")
    assert validate_file(p) == []


def test_missing_uid_flagged(tmp_path):
    p = tmp_path / "bad.ics"
    p.write_text(_VALID.replace("UID:u@d\r\n", ""), encoding="utf-8")
    assert any("UID" in e for e in validate_file(p))


def test_long_line_flagged(tmp_path):
    p = tmp_path / "long.ics"
    p.write_text(_VALID.replace("SUMMARY:Ireland v England", "SUMMARY:" + "Z" * 200), encoding="utf-8")
    assert any("octets" in e for e in validate_file(p))


def test_validate_paths_zero_on_valid(tmp_path):
    p = tmp_path / "ok.ics"
    p.write_text(_VALID, encoding="utf-8")
    assert validate_paths([p]) == 0
