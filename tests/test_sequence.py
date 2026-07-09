"""SEQUENCE state manager: increments on change, carries prior kickoff."""
from scripts.sequence_state import SequenceState


def test_first_seen_uid_returns_zero(tmp_state_dir):
    st = SequenceState(tmp_state_dir / "seq.json")
    seq, prior = st.next_sequence("u1", "h1", "2027-02-05T20:10:00+00:00")
    assert seq == 0
    assert prior is None


def test_unchanged_content_same_sequence(tmp_state_dir):
    st = SequenceState(tmp_state_dir / "seq.json")
    st.next_sequence("u1", "h1", "T1")
    seq, _ = st.next_sequence("u1", "h1", "T1")
    assert seq == 0


def test_changed_content_increments(tmp_state_dir):
    st = SequenceState(tmp_state_dir / "seq.json")
    st.next_sequence("u1", "h1", "T1")
    seq, _ = st.next_sequence("u1", "h2", "T1")
    assert seq == 1


def test_prior_kickoff_returned_on_content_change(tmp_state_dir):
    st = SequenceState(tmp_state_dir / "seq.json")
    st.next_sequence("u1", "h1", "2026-07-04T05:10:00+00:00")
    seq, prior = st.next_sequence("u1", "h2", None)  # became played, kickoff gone
    assert seq == 1
    assert prior == "2026-07-04T05:10:00+00:00"


def test_state_persists_across_load(tmp_state_dir):
    p = tmp_state_dir / "seq.json"
    st = SequenceState(p)
    st.next_sequence("u1", "h1", "T1")
    st.save()
    st2 = SequenceState(p)
    seq, _ = st2.next_sequence("u1", "h1", "T1")
    assert seq == 0
