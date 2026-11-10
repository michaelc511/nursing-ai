"""Every state-changing service writes an audit_log row through here."""
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.repositories import cases as repo


def log(session: Session, actor: str, action: str, case_id: int | None = None, **details) -> None:
    repo.add(session, AuditLog(case_id=case_id, actor=actor, action=action, details=details))
