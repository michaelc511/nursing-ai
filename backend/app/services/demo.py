"""Demo tools (Phase 2.5, Claude's additions): test-only `mark`, and `reset-demo`."""
import shutil

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, NotFound
from app.repositories import cases as repo
from app.repositories.blob import get_blob_storage
from app.services import auth, state, sync

MARK_TARGETS = {"ready": state.READY, "incomplete": state.INCOMPLETE}


def mark(session: Session, case_id: int, target: str, note: str = "", actor: str = "cli") -> str:
    """Stand-in for AI review until Phase 3: Received -> ReadyForReview | Incomplete (audited)."""
    if target not in MARK_TARGETS:
        raise AppError("Use 'ready' or 'incomplete'")
    case = repo.get_case(session, case_id)
    if case is None:
        raise NotFound(f"Case {case_id} not found")
    state.transition(session, case, MARK_TARGETS[target], actor, reason=note or "manual mark (test-only)")
    if case.status == state.INCOMPLETE:
        sync.send_provider_request(session, case, actor=actor)
    return case.status


def reset_demo(session: Session, actor: str = "cli") -> dict:
    """Wipe cases + storage + inbox, re-seed reviewers, copy the samples into the inbox."""
    if not settings.demo_mode:
        from app.errors import Forbidden
        raise Forbidden("reset-demo needs DEMO_MODE=true in .env")
    repo.delete_all_case_data(session)
    get_blob_storage().clear()
    inbox = settings.inbox_dir
    inbox.mkdir(parents=True, exist_ok=True)
    for f in inbox.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            f.unlink()
    auth.seed_reviewers(session)
    copied = []
    if settings.samples_dir.exists():
        for f in sorted(settings.samples_dir.glob("*.pdf")):
            shutil.copyfile(f, inbox / f.name)
            copied.append(f.name)
    from app.services import audit
    audit.log(session, actor, "demo_reset", inbox=copied)
    return {"cleared": True, "inbox": copied}
