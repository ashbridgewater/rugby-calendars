"""Pytest bootstrap: make the repo root importable and expose fixture helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_DIR = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> str:
    """Read a saved HTML fixture by filename."""
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture
def load_html():
    return load_fixture


@pytest.fixture
def tmp_state_dir(tmp_path: Path) -> Path:
    d = tmp_path / "state"
    d.mkdir()
    return d
