"""Read side: queue, case detail, metrics, stuck cases."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.errors import NotFound
from app.models import Case, utcnow
from app.repositories import cases as repo
from app.repositories.blob import get_blob_storage
from app.services import policy, state

OPEN_STATUSES = [state.RECEIVED, state.INCOMPLETE, state.READY, state.PENDED]

SOURCE_PREFIX = {"fax": "FAX", "upload": "UPL", "portal": "PRT"}


def doc_id(case: Case) -> str:
    """Intake reference, e.g. FAX-20261110-0001 (source + received date + case number)."""
    return f"{SOURCE_PREFIX.get(case.source, 'DOC')}-{case.received_at:%Y%m%d}-{case.id:04d}"


def description(case: Case) -> str:
    p = policy.policy_for_case(case)
    service = f"{p['title']} (CPT {p['cpt']})" if p else "Prior auth request (service not identified yet)"
    return f"{service} · {case.diagnosis}" if case.diagnosis else service


def _tier(session: Session, case: Case) -> str | None:
    r = repo.latest_review(session, case.id)
    return r.tier if r else None


def summary(session: Session, case: Case) -> dict:
    r = repo.latest_review(session, case.id)
    return {"ai_engine": (r.result or {}).get("engine") if r else None,"id": case.id, "doc_id": doc_id(case), "description": description(case),
            "source": case.source, "filename": case.filename, "status": case.status,
            "tier": r.tier if r else None, "received_at": case.received_at.isoformat(),
            "status_changed_at": case.status_changed_at.isoformat(), "sync_status": case.sync_status}


def list_cases(session: Session, status: str | None = None, tier: str | None = None) -> list[dict]:
    rows = [summary(session, c) for c in repo.list_cases(session, status)]
    return [r for r in rows if tier is None or r["tier"] == tier]


def get_case(session: Session, case_id: int) -> Case:
    case = repo.get_case(session, case_id)
    if case is None:
        raise NotFound(f"Case {case_id} not found")
    return case


def detail(session: Session, case_id: int) -> dict:
    from app.services import review as review_svc
    case = get_case(session, case_id)
    review = repo.latest_review(session, case.id)
    return {**summary(session, case),
            "ai_label": (review.result or {}).get("engine") if review else review_svc.engine().label,
            "sync_detail": case.sync_detail,
            "policy": policy.policy_for_case(case),
            "extra_documents": [d["filename"] for d in (case.extra_documents or [])],
            "ai_review": review.result if review else None,
            "ai_reviewed_at": review.created_at.isoformat() if review else None,
            "decisions": [{"decision": d.decision, "rationale": d.rationale, "override": d.override,
                           "ai_tier": d.ai_tier, "reviewer": d.reviewer.full_name,
                           "role": d.reviewer.role, "at": d.created_at.isoformat()}
                          for d in case.decisions],
            "audit": [{"actor": a.actor, "action": a.action, "details": a.details, "at": a.at.isoformat()}
                      for a in repo.audit_for_case(session, case.id)],
            "allowed_actions": ["Approve", "Deny", "Pend"] if case.status in (state.READY, state.PENDED) else []}


def document_path(session: Session, case_id: int, index: int = 0, actor: str | None = None):
    """index 0 = main document; 1.. = extra documents. Returns (path, filename).
    With `actor` (a download), the download is written to the audit log (patient record left the app)."""
    case = get_case(session, case_id)
    docs = [{"filename": case.filename, "blob_path": case.blob_path}, *(case.extra_documents or [])]
    if index < 0 or index >= len(docs):
        raise NotFound("Document not found")
    if actor:
        from app.services import audit
        audit.log(session, actor, "document_downloaded", case.id, filename=docs[index]["filename"], index=index)
    return get_blob_storage().path(docs[index]["blob_path"]), docs[index]["filename"]


def stuck(session: Session, days: float) -> list[dict]:
    before = utcnow() - timedelta(days=days)
    out = []
    for c in repo.cases_in_status_before(session, before, OPEN_STATUSES):
        age = (utcnow() - c.status_changed_at).total_seconds() / 86400
        out.append({**summary(session, c), "days_in_status": round(age, 1)})
    return out


def metrics(session: Session) -> dict:
    """Success metrics from CLAUDE.md: turnaround, rework %, cases reviewed, override rate."""
    cases = repo.list_cases(session)
    decisions = repo.all_decisions(session)
    final = [d for d in decisions if d.decision in (state.APPROVED, state.DENIED)]
    by_case = {}
    for d in final:
        by_case.setdefault(d.case_id, d)
    turnaround = [(d.created_at - d.case.received_at).total_seconds() / 86400 for d in by_case.values()]
    reworked = repo.ever_incomplete_case_ids(session)
    with_tier = [d for d in final if d.ai_tier]
    return {
        "total_cases": len(cases),
        "by_status": repo.count_by_status(session),
        "cases_reviewed": len({d.case_id for d in decisions}),
        "avg_turnaround_days": round(sum(turnaround) / len(turnaround), 2) if turnaround else None,
        "rework_rate": round(len(reworked) / len(cases), 3) if cases else None,
        "override_rate": round(sum(d.override for d in with_tier) / len(with_tier), 3) if with_tier else None,
    }
