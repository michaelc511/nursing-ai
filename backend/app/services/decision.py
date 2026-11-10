"""Layer 4: human decisions. Only a logged-in nurse/medical director can set Approved/Denied/Pended."""
from sqlalchemy.orm import Session

from app.errors import AppError, Forbidden, NotFound
from app.models import Decision, Reviewer
from app.repositories import cases as repo
from app.services import audit, state, sync

DECISIONS = {"Approve": state.APPROVED, "Deny": state.DENIED, "Pend": state.PENDED}
REVIEWER_ROLES = {"nurse", "medical_director"}


def is_override(decision: str, ai_tier: str | None) -> bool:
    """Nurse disagreed with the AI tier."""
    return (decision == state.APPROVED and ai_tier == "likely_deny") or \
           (decision == state.DENIED and ai_tier == "likely_approve")


def decide(session: Session, case_id: int, reviewer: Reviewer, action: str, rationale: str) -> Decision:
    if reviewer is None or reviewer.role not in REVIEWER_ROLES:
        raise Forbidden("Only a nurse or medical director can decide")
    if action not in DECISIONS:
        raise AppError(f"Unknown decision {action!r} (use Approve, Deny or Pend)")
    if action == "Deny" and reviewer.role != "medical_director":
        raise Forbidden("Only a Medical Director can deny (adverse determination). Pend it for MD review.")
    if not rationale or not rationale.strip():
        raise AppError("A rationale is required")
    case = repo.get_case(session, case_id)
    if case is None:
        raise NotFound(f"Case {case_id} not found")
    target = DECISIONS[action]
    if case.status == state.PENDED:
        state.transition(session, case, state.READY, reviewer.username, reason="review resumed")
    review = repo.latest_review(session, case.id)
    tier = review.tier if review else None
    state.transition(session, case, target, reviewer.username, human=True, reason=rationale.strip())
    d = repo.add(session, Decision(case_id=case.id, reviewer_id=reviewer.id, decision=target,
                                   rationale=rationale.strip(), ai_tier=tier,
                                   override=is_override(target, tier)))
    audit.log(session, reviewer.username, "decision", case.id, decision=target, rationale=d.rationale,
              ai_tier=tier, override=d.override, role=reviewer.role)
    if target in (state.APPROVED, state.DENIED):
        sync.sync_decision(session, case, actor="system")
    return d
