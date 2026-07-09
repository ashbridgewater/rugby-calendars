"""RFC5545 text escaping + octet-safe line folding."""
from scripts.ics_utils import escape_text, fold_line, unfold


def test_escape_semicolon():
    assert escape_text("Aviva Stadium; Dublin") == r"Aviva Stadium\; Dublin"


def test_escape_comma():
    assert escape_text("Twickenham, London") == r"Twickenham\, London"


def test_escape_backslash():
    assert escape_text("a\\b") == "a\\\\b"


def test_escape_newline():
    assert escape_text("line1\nline2") == r"line1\nline2"


def test_escape_backslash_done_first():
    # a literal backslash becomes two; a semicolon becomes \; -> no double-escaping
    assert escape_text("\\") == "\\\\"
    assert escape_text(";") == r"\;"


def test_fold_short_line_unchanged():
    s = "SUMMARY:England v Wales"
    assert fold_line(s) == s


def test_fold_long_ascii_first_segment_is_75_octets():
    folded = fold_line("X" * 100)
    parts = folded.split("\r\n")
    assert len(parts[0].encode("utf-8")) == 75
    assert parts[1].startswith(" ")


def test_fold_never_splits_multibyte_codepoint():
    line = "a" * 74 + "\u00e9" * 6  # é is 2 octets
    folded = fold_line(line)
    for seg in folded.split("\r\n"):
        seg.encode("utf-8").decode("utf-8")  # raises if a codepoint was split


def test_fold_roundtrips_via_unfold():
    line = "SUMMARY:" + "caf\u00e9 " * 30 + "\u65e5\u672c " * 10
    assert unfold(fold_line(line)) == line
