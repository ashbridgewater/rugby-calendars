"""RFC5545 helpers: TEXT escaping and octet-safe line folding."""
from __future__ import annotations

_MAX_OCTETS = 75


def escape_text(value: str) -> str:
    """Escape a value for an RFC5545 TEXT property.

    Backslash is escaped first so subsequent escapes are not doubled.
    """
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
    return value


def fold_line(line: str) -> str:
    """Fold one logical line to <=75 octets per segment without splitting a codepoint.

    Continuation segments start with a single space (which counts toward the 75)
    and segments are joined with CRLF, per RFC5545 s3.1.
    """
    if len(line.encode("utf-8")) <= _MAX_OCTETS:
        return line
    segments: list[str] = []
    current = ""
    current_octets = 0
    for ch in line:
        cb = len(ch.encode("utf-8"))
        if current_octets + cb > _MAX_OCTETS:
            segments.append(current)
            current = " " + ch  # leading space of a continuation line
            current_octets = 1 + cb
        else:
            current += ch
            current_octets += cb
    segments.append(current)
    return "\r\n".join(segments)


def unfold(text: str) -> str:
    """Inverse of :func:`fold_line` (used in tests / validation)."""
    return text.replace("\r\n ", "").replace("\n ", "")
