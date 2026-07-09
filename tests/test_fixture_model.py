"""Fixture dataclass + Provider protocol contract."""
import dataclasses
from datetime import datetime, timezone

import pytest

from scripts.providers.base import Fixture, Provider

UTC = timezone.utc


def _mk(**kw) -> Fixture:
    base = dict(
        tournament="autumn",
        season=2026,
        stage="Round 4",
        home="England",
        away="Australia",
        venue="Allianz Stadium, Twickenham",
        status="scheduled",
        source_url="https://example.test/",
        uid="england-v-australia@rc",
        kickoff_utc=datetime(2026, 11, 8, 15, 10, tzinfo=UTC),
    )
    base.update(kw)
    return Fixture(**base)


def test_fixture_is_frozen():
    f = _mk()
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.home = "X"  # type: ignore[misc]


def test_kickoff_utc_must_be_aware():
    with pytest.raises(ValueError):
        _mk(kickoff_utc=datetime(2026, 11, 8, 15, 10))  # naive -> rejected


def test_invalid_status_rejected():
    with pytest.raises(ValueError):
        _mk(status="bogus")


def test_involves_matches_xv_and_case():
    f = _mk(home="England XV", away="France XV")
    assert f.involves("England")
    assert f.involves("france")
    assert not f.involves("Wales")


def test_provider_protocol_has_fetch():
    assert hasattr(Provider, "fetch")
