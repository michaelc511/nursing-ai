import pytest

from app.errors import InvalidTransition
from app.repositories import cases as repo
from app.services import state

ALLOWED_AUTO = [("Received", "Incomplete"), ("Received", "ReadyForReview"),
                ("Incomplete", "Received"), ("Pended", "ReadyForReview"),
                ("Approved", "Synced"), ("Denied", "Synced")]
HUMAN = [("ReadyForReview", "Approved"), ("ReadyForReview", "Denied"), ("ReadyForReview", "Pended")]


@pytest.mark.parametrize("src,dst", ALLOWED_AUTO)
def test_allowed_transitions(session, make_case, src, dst):
    c = make_case(src)
    state.transition(session, c, dst, "system")
    assert c.status == dst


@pytest.mark.parametrize("src,dst", HUMAN)
def test_human_transitions_need_human(session, make_case, src, dst):
    c = make_case(src)
    with pytest.raises(InvalidTransition):
        state.transition(session, c, dst, "system")
    state.transition(session, c, dst, "nurse1", human=True)
    assert c.status == dst


def test_every_other_transition_rejected(session, make_case):
    allowed = set(ALLOWED_AUTO) | set(HUMAN)
    for src in state.STATUSES:
        for dst in state.STATUSES:
            if (src, dst) in allowed:
                continue
            c = make_case(src)
            with pytest.raises(InvalidTransition):
                state.transition(session, c, dst, "nurse1", human=True)
            assert c.status == src


def test_transition_writes_audit_row(session, make_case):
    c = make_case("Received")
    state.transition(session, c, "ReadyForReview", "cli", reason="test")
    rows = repo.audit_for_case(session, c.id)
    assert len(rows) == 1
    assert rows[0].details == {"from": "Received", "to": "ReadyForReview", "reason": "test"}
    assert rows[0].actor == "cli"
