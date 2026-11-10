"""DB access for cases, reviews, decisions, audit log and reviewers. Only this layer queries."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIReview, AuditLog, Case, Decision, Reviewer


def add(session: Session, obj):
    session.add(obj)
    session.flush()
    return obj


def get_case(session: Session, case_id: int) -> Case | None:
    return session.get(Case, case_id)


def list_cases(session: Session, status: str | None = None) -> list[Case]:
    q = select(Case).order_by(Case.received_at.desc())
    if status:
        q = q.where(Case.status == status)
    return list(session.scalars(q))


def cases_in_status_before(session: Session, before: datetime, statuses: list[str]) -> list[Case]:
    q = select(Case).where(Case.status.in_(statuses), Case.status_changed_at < before)
    return list(session.scalars(q.order_by(Case.status_changed_at)))


def count_by_status(session: Session) -> dict[str, int]:
    rows = session.execute(select(Case.status, func.count()).group_by(Case.status))
    return {s: n for s, n in rows}


def latest_review(session: Session, case_id: int) -> AIReview | None:
    q = select(AIReview).where(AIReview.case_id == case_id).order_by(AIReview.id.desc())
    return session.scalars(q).first()


def all_decisions(session: Session) -> list[Decision]:
    return list(session.scalars(select(Decision)))


def audit_for_case(session: Session, case_id: int) -> list[AuditLog]:
    q = select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.id)
    return list(session.scalars(q))


def ever_incomplete_case_ids(session: Session) -> set[int]:
    ids = set()
    for row in session.execute(select(AuditLog.case_id, AuditLog.details).where(AuditLog.action == "status_change")):
        if row.details.get("to") == "Incomplete":
            ids.add(row.case_id)
    return ids


def get_reviewer_by_username(session: Session, username: str) -> Reviewer | None:
    return session.scalars(select(Reviewer).where(Reviewer.username == username)).first()


def list_reviewers(session: Session) -> list[Reviewer]:
    return list(session.scalars(select(Reviewer).order_by(Reviewer.id)))


def delete_all_case_data(session: Session) -> None:
    for model in (AuditLog, Decision, AIReview, Case):
        session.query(model).delete()
