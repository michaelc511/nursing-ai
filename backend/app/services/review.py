"""Layer 2: AI review. Reads a stored case, gets the policy, asks the AI engine, verifies, saves.

AI suggests, code verifies, people decide:
- #2a  Python reads the CPT from the PDF text (regex) before the policy lookup (#3).
- #2b  The engine (AI_MODE=mock -> "AI-MK", AI_MODE=claude -> Phase 3) returns a ReviewResult.
- Code validates the schema, cross-checks CPT, verifies every quote against the PDF text,
  forces "needs_review" on any mismatch, saves ai_reviews, and moves Received -> Ready / Incomplete.
The AI can never set Approved, Pended or Denied (state machine: human-only).
"""
import json
import re
from pathlib import Path

from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, NotFound
from app.models import AIReview, Case
from app.repositories import cases as repo
from app.repositories.blob import get_blob_storage
from app.schemas.review import ReviewResult
from app.services import audit, intake, policy, state, sync

CPT_RE = re.compile(r"\bCPT:\s*(\d{5})\b")


# ---------------------------------------------------------------- engines

class MockEngine:
    """Prepared answers per demo sample, in the exact Claude output shape. Always labeled AI-MK."""
    label = "AI-MK"
    version = "mock-v1"

    def review(self, case: Case, docs: list[Path], policy_info: dict | None, session: Session | None = None,
               actor: str | None = None, feedback: str | None = None) -> dict:
        folder = settings.samples_dir / "mock_reviews"
        stem = Path(case.filename).stem
        candidates = ([folder / f"{stem}.with_docs.json"] if len(docs) > 1 else []) + [folder / f"{stem}.json"]
        for f in candidates:
            if f.exists():
                return json.loads(f.read_text())
        # Unknown file: send it to a person (Ready for review, needs review), never back to the provider.
        return {"fields": {}, "complete": True, "tier": "needs_review", "criteria": [],
                "summary": "AI-MK has no prepared answer for this document. A person needs to review it."}


class ClaudeEngine:
    """Real Claude (AI_MODE=claude). PDFs go to Claude natively; policy chunks from RAG (#4) as data.

    Output is the same ReviewResult schema (structured output, Pydantic-validated). Usage, cost and
    latency are recorded per call (F6); identical inputs reuse the cached answer (N3); if every
    model fails, the case goes to a person with a warning (never a silent mock answer).
    """
    label = "AI"
    version = "claude-review_v1"
    ready = True

    def review(self, case: Case, docs: list[Path], policy_info: dict | None, session: Session | None = None,
               actor: str | None = None, feedback: str | None = None) -> dict:
        import base64
        from app.llm import client as llm
        from app.prompts import load
        system = load("review_v1")
        blobs = [p.read_bytes() for p in docs]
        content: list = []
        for i, b in enumerate(blobs):
            content.append({"type": "document", "title": f"document {i}",
                            "source": {"type": "base64", "media_type": "application/pdf",
                                       "data": base64.b64encode(b).decode()}})
        chunks = (policy_info or {}).get("chunks") or []
        pol_text = "\n\n".join(c["text"] for c in chunks) or "(no policy found for this CPT)"
        content.append({"type": "text", "text": (
            f"<cpt_read_by_code>{case.cpt or 'not found'}</cpt_read_by_code>\n"
            f"<policy_chunks>\n{pol_text}\n</policy_chunks>\n"
            "Review this prior authorization request against the policy and return the JSON.")})
        if feedback:   # retry from the verify node: tell Claude exactly which checks failed
            content.append({"type": "text", "text": f"<code_check_failures>\n{feedback}\n</code_check_failures>\n"
                            "Your previous answer failed these code checks. Copy quotes exactly from the documents, "
                            "or mark the criterion unclear."})
        try:
            out = llm.parse(session, purpose="review", system=system, content=content, schema=ReviewResult,
                            case_id=case.id, actor=actor,
                            cache_parts=None if feedback else [
                                llm.cache_key(*blobs), (policy_info or {}).get("version"),
                                [c["id"] for c in chunks], llm.current_model(session), self.version])
        except llm.LLMUnavailable as e:
            return unavailable_result(str(e))
        return out.model_dump()


def unavailable_result(why: str) -> dict:
    """N3 production fallback: no AI answer -> a person reviews the case (Ready for review, needs review)."""
    return {"fields": {}, "complete": True, "tier": "needs_review", "criteria": [],
            "summary": "The AI review is unavailable right now. A person needs to review this request.",
            "warnings": [f"AI unavailable: {why[:200]}"]}


def engine():
    from app.services import ai_mode
    return ClaudeEngine() if ai_mode.current() == "claude" else MockEngine()


# ---------------------------------------------------------------- helpers

def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def pdf_pages(path: Path) -> list[str]:
    """Text per page ([] if the file can't be read as a PDF, e.g. a scan or a bad upload)."""
    from app.services import parsing                     # N1: OCR for scanned pages
    return [_norm(t) for t in parsing.page_texts(path)]


def _in(pages: list[str], page: int, quote: str) -> bool:
    return 1 <= page <= len(pages) and _norm(quote) in pages[page - 1]


def read_cpt(path: Path) -> str | None:
    """#2a: Python reads the CPT straight from the request form."""
    for text in pdf_pages(path)[:2]:
        m = CPT_RE.search(text.upper())
        if m:
            return m.group(1)
    return None


def case_docs(case: Case) -> list[Path]:
    store = get_blob_storage()
    return [store.path(case.blob_path), *[store.path(d["blob_path"]) for d in (case.extra_documents or [])]]


def verify(result: ReviewResult, docs: list[Path], policy_pdf: Path | None, cpt_read: str | None) -> ReviewResult:
    doc_pages = [pdf_pages(p) for p in docs]
    pol_pages = pdf_pages(policy_pdf) if policy_pdf else []
    warnings = list(result.warnings)
    for c in result.criteria:
        for e in c.request_evidence:
            e.verified = e.doc < len(doc_pages) and _in(doc_pages[e.doc], e.page, e.quote)
            if not e.verified:
                warnings.append(f"Quote not found in document {e.doc + 1}, page {e.page}: \"{e.quote[:60]}\"")
        if c.policy_evidence:
            c.policy_evidence.verified = _in(pol_pages, c.policy_evidence.page, c.policy_evidence.quote)
            if not c.policy_evidence.verified:
                warnings.append(f"Policy quote not found on page {c.policy_evidence.page}")
    if cpt_read and result.fields.cpt and cpt_read != result.fields.cpt:
        warnings.append(f"CPT mismatch: form says {cpt_read}, AI read {result.fields.cpt}")
    if not policy_pdf:
        warnings.append("No policy found for this request's CPT code")
    result.warnings = warnings
    if warnings:
        result.tier = "needs_review"
    return result


def guard_check(result: ReviewResult, docs: list[Path]) -> ReviewResult:
    """F22: instruction-like text in a patient document, or a leak in the AI output -> a person checks."""
    from app import guard
    flags = [f for p in docs for page in pdf_pages(p) for f in guard.scan_document(page)]
    for f in flags:
        result.warnings.append(f"Instruction-like text in a document (ignored by the AI): \"{f}\"")
    for text in (result.summary, result.draft_provider_request or ""):
        try:
            guard.check_output(text)
        except guard.Blocked as b:
            result.warnings.append(f"AI output blocked ({b.reason})")
            result.summary = "The AI output was blocked by a safety check. A person needs to review this request."
            result.draft_provider_request = None
    if result.warnings:
        result.tier = "needs_review"
    return result


# ---------------------------------------------------------------- service

def review_case(session: Session, case_id: int, actor: str = "system") -> AIReview:
    """Entry point (REST, CLI, MCP, run_all). REVIEW_PIPELINE=graph (default, LangGraph) | linear (baseline)."""
    if settings.review_pipeline == "linear":
        return review_case_linear(session, case_id, actor)
    from app.services import review_graph
    return review_graph.run(session, case_id, actor)


def save_review(session: Session, case: Case, eng, result: ReviewResult, pol: dict | None, chunks: list,
                actor: str, pipeline: str, steps: list | None = None) -> AIReview:
    """Persist the review and move Received -> Ready / Incomplete (never a decision)."""
    if result.fields.cpt and not case.cpt:
        case.cpt = result.fields.cpt
    if result.fields.diagnosis:
        case.diagnosis = f"{result.fields.diagnosis} ({result.fields.icd10})" if result.fields.icd10 else result.fields.diagnosis
    pol_meta = {k: v for k, v in pol.items() if k != "chunks"} if pol else None
    rag = [{k: c[k] for k in ("id", "label", "section_title", "page", "score", "quote")} for c in chunks]
    data = {**result.model_dump(), "engine": eng.label, "policy": pol_meta, "policy_chunks": rag,
            "pipeline": {"name": pipeline, "steps": steps or []}}
    review = repo.add(session, AIReview(case_id=case.id, result=data, tier=result.tier, prompt_version=eng.version))
    audit.log(session, eng.label, "ai_review", case.id, tier=result.tier, complete=result.complete,
              warnings=len(result.warnings), requested_by=actor)
    if case.status == state.RECEIVED:
        target = state.READY if result.complete else state.INCOMPLETE
        state.transition(session, case, target, eng.label, reason=f"{eng.label} review: {result.tier}")
        if target == state.INCOMPLETE:
            sync.send_provider_request(session, case, actor=eng.label)
    return review


def review_case_linear(session: Session, case_id: int, actor: str = "system") -> AIReview:
    """F12.1 baseline: the original one-pass review, kept frozen next to the LangGraph pipeline."""
    case = repo.get_case(session, case_id)
    if case is None:
        raise NotFound(f"Case {case_id} not found")
    eng = engine()
    docs = case_docs(case)
    cpt_read = read_cpt(docs[0])                                   # #2a (Python)
    if cpt_read:
        case.cpt = cpt_read
    pol = policy.policy_for_case(case)                             # #3
    pol_pdf = policy.policy_path(pol["cpt"])[0] if pol else None
    chunks = policy.criteria_for_review(pol["cpt"], " ".join(pdf_pages(docs[0])[:1])) if pol else []  # #4 RAG
    if pol:
        pol = {**pol, "chunks": chunks}
    raw = eng.review(case, docs, pol, session=session, actor=actor)  # #2b (AI)
    if eng.label == "AI-MK":
        from app.llm import client as llm
        llm.record(session, purpose="review", engine="AI-MK", model="AI-MK", case_id=case.id, actor=actor)
    try:
        result = ReviewResult.model_validate(raw)
    except ValidationError:
        raw = eng.review(case, docs, pol, session=session, actor=actor)  # retry once
        try:
            result = ReviewResult.model_validate(raw)
        except ValidationError as e:
            raise AppError(f"{eng.label} returned an invalid review: {e.error_count()} problem(s)")
    result = verify(result, docs, pol_pdf, cpt_read)
    result = guard_check(result, docs)                             # F22
    return save_review(session, case, eng, result, pol, chunks, actor, pipeline="linear")


def review_received(session: Session, actor: str) -> list[int]:
    ids = [c.id for c in repo.list_cases(session, state.RECEIVED)]
    for cid in sorted(ids):
        review_case(session, cid, actor)
    return sorted(ids)


def run_all(session: Session, actor: str, trigger: str) -> dict:
    """Poll the inbox, then AI-review every Received case. Same run for Cowork, web and CLI."""
    created = [c.id for c in intake.poll_inbox(session, actor=actor)]
    session.flush()
    reviewed = review_received(session, actor)
    summary = summarize(session, created, reviewed, trigger)
    audit.log(session, actor, "run_all", None, **summary)
    return summary


def summarize(session: Session, created: list[int], reviewed: list[int], trigger: str) -> dict:
    from app.services import cases as cases_svc
    incomplete, ready = [], {}
    for cid in reviewed:
        c = repo.get_case(session, cid)
        r = repo.latest_review(session, cid)
        if c.status == state.INCOMPLETE:
            miss = ", ".join(m["item"] for m in (r.result.get("missing") or [])) if r else ""
            incomplete.append({"id": cid, "doc_id": cases_svc.doc_id(c), "missing": miss})
        elif c.status == state.READY and r:
            ready[r.tier] = ready.get(r.tier, 0) + 1
    return {"trigger": trigger, "engine": engine().label, "new": len(created), "reviewed": len(reviewed),
            "incomplete": incomplete, "ready_by_tier": ready, "stuck": len(cases_svc.stuck(session, 2))}


def last_run(session: Session) -> dict | None:
    from sqlalchemy import select
    from app.models import AuditLog
    row = session.scalars(select(AuditLog).where(AuditLog.action == "run_all").order_by(AuditLog.id.desc())).first()
    return {**row.details, "at": row.at.isoformat(), "actor": row.actor} if row else None
