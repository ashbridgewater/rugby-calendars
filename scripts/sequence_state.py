"""Persistent per-UID SEQUENCE + prior-kickoff tracking.

State lives in a JSON file (``state/sequence.json``) committed to the repo so
that across runs:
  * SEQUENCE only increments when an event's content actually changed
    (calendar clients apply updates in place when UID matches + SEQUENCE rises);
  * a played match that has lost its kickoff time on the source page can reuse
    the kickoff we previously recorded.
"""
from __future__ import annotations

import json
from pathlib import Path


class SequenceState:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def next_sequence(
        self,
        uid: str,
        content_hash: str,
        kickoff_iso: str | None,
    ) -> tuple[int, str | None]:
        """Return (sequence, prior_kickoff_iso) and record the new state.

        prior_kickoff_iso is whatever kickoff we had stored *before* this call,
        letting a now-played fixture fall back to its original time.
        """
        entry = self._data.get(uid)
        prior_kickoff = entry.get("kickoff_utc") if entry else None
        if entry is None:
            seq = 0
        elif entry.get("content_hash") == content_hash:
            seq = int(entry.get("sequence", 0))
        else:
            seq = int(entry.get("sequence", 0)) + 1
        stored_kickoff = kickoff_iso if kickoff_iso is not None else prior_kickoff
        self._data[uid] = {
            "content_hash": content_hash,
            "sequence": seq,
            "kickoff_utc": stored_kickoff,
        }
        return seq, prior_kickoff

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
