"""Case status state machine (CLAUDE.md). All status changes go through transition()."""
from sqlalchemy.orm import Session

from app.errors import InvalidTransition
from app.models import Case, utcnow
from app.services import audit

RECEIVED, INCOMPLETE, READY = "Received", "Incomplete", "ReadyForReview"
APPROVED, DENIED, PENDED, SYNCED = "Approved", "Denied", "Pended", "Synced"
STATUSES = [RECEIVED, INCOMPLETE, READY, APPROVED, DENIED, PENDED, SYNCED]
HUMAN_ONLY = {APPROVED, DENIED, PENDED}

ALLOWED: dict[str, set[str]] = {
    RECEIVED: {INCOMPLETE, READY},
    INCOMPLETE: {RECEIVED},
    READY: {APPROVED, DENIED, PENDED},
    PENDED: {READY},
    APPROVED: {SYNCED},
    DENIED: {SYNCED},
    SYNCED: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED.get(current, set())


def transition(session: Session, case: Case, target: str, actor: str, *, human: bool = False,
               reason: str = "") -> Case:
    """Move a case to `target`. Approved/Denied/Pended need human=True (set only by decision service)."""
    if target in HUMAN_ONLY and not human:
        raise InvalidTransition(f"{target} can only be set by a human reviewer")
    if not can_transition(case.status, target):
        raise InvalidTransition(f"Cannot move case {case.id} from {case.status} to {target}")
    old = case.status
    case.status = target
    case.status_changed_at = utcnow()
    audit.log(session, actor, "status_change", case.id, **{"from": old, "to": target, "reason": reason})
    return case
