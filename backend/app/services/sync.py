"""Layer 5: systems of record (mocked). UM platform push + provider notification."""
from sqlalchemy.orm import Session

from app.models import Case
from app.repositories import cases as repo
from app.services import audit, state


def _mock_um_push(case: Case) -> str:
    return f"UM-{case.id:06d}"  # a real integration returns the UM platform's reference


def _mock_notify_provider(case: Case, message: str) -> None:
    """Mock notifier: a real one would fax/portal-message the provider."""
    return None


def sync_decision(session: Session, case: Case, actor: str = "system") -> Case:
    """Approved/Denied -> push to UM + notify provider -> Synced."""
    decision = case.status
    case.sync_status = "pending"
    ref = _mock_um_push(case)
    _mock_notify_provider(case, f"Prior authorization {decision.lower()} (ref {ref}).")
    case.sync_status = "synced"
    case.sync_detail = f"UM ref {ref}; provider notified: {decision}"
    audit.log(session, actor, "synced", case.id, um_ref=ref, decision=decision, provider_notified=True)
    state.transition(session, case, state.SYNCED, actor, reason=f"synced to UM ({ref})")
    return case


def send_provider_request(session: Session, case: Case, actor: str = "system") -> str:
    """Incomplete case: send the drafted provider request (from the AI review when it exists)."""
    review = repo.latest_review(session, case.id)
    draft = (review.result or {}).get("draft_provider_request") if review else None
    message = draft or f"Case {case.id}: documentation incomplete. Please send the missing records."
    _mock_notify_provider(case, message)
    case.sync_detail = "provider request sent"
    audit.log(session, actor, "provider_request_sent", case.id, message=message)
    return message
