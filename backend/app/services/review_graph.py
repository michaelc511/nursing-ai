"""Phase 5 (F13, F13.1): the AI review as a LangGraph state machine.

    read_form -> rewrite_query -> retrieve_policy -> ai_review -> verify --(quotes failed, retry allowed)--> ai_review
                                                    \\--> route (save + Received -> Ready/Incomplete)

- read_form, retrieve_policy, verify, route are Python (README: "Python does every rule, check,
  status change and log entry"); ai_review is the only node that calls the AI (Claude or AI-MK).
- verify -> ai_review retries once, Claude only, with the failed checks as feedback, and only while
  the case is under MAX_CASE_COST_USD. Step cap: STEP_CAP nodes per run (recursion limit).
- No node can approve, pend or deny: route only moves Received -> ReadyForReview | Incomplete.
- Each node's time is kept in steps[] and saved with the review (trace, Phase 8).
"""
import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError, NotFound
from app.repositories import cases as repo
from app.schemas.review import ReviewResult
from app.llm import client as llm
from app.llm import tracing
from app.services import policy

STEP_CAP = 9          # read_form, rewrite, retrieve, ai, verify, ai, verify, route (+1 spare)
MAX_ATTEMPTS = 2


class ReviewState(TypedDict, total=False):
    case_id: int
    actor: str
    cpt_read: str | None
    query: str
    rewritten: str | None
    pol: dict | None
    chunks: list
    result: dict
    attempts: int
    feedback: str | None
    review_id: int
    steps: Annotated[list, operator.add]


def _timed(name, fn):
    def node(s: ReviewState):
        t0 = time.monotonic()
        out = fn(s) or {}
        out["steps"] = [{"node": name, "ms": int((time.monotonic() - t0) * 1000)}]
        return out
    return node


def build(session: Session):
    from app.services import review as rv
    eng = rv.engine()

    def case_and_docs(s):
        case = repo.get_case(session, s["case_id"])
        return case, rv.case_docs(case)

    def read_form(s):
        case, docs = case_and_docs(s)
        cpt = rv.read_cpt(docs[0])                           # #2a regex (OCR-aware)
        if cpt:
            case.cpt = cpt
        first_page = " ".join(rv.pdf_pages(docs[0])[:1])
        return {"cpt_read": cpt, "query": first_page}

    def rewrite_query(s):
        from app.services import query_rewrite                # S8 (Claude mode only)
        rw = query_rewrite.rewrite(session, s.get("query", "")[:1500], s["case_id"], s["actor"])
        return {"rewritten": rw if rw != s.get("query") else None}

    def retrieve_policy(s):
        case, _ = case_and_docs(s)
        pol = policy.policy_for_case(case)                   # #3 CPT -> policy
        chunks = policy.criteria_for_review(pol["cpt"], s.get("query", ""),
                                            extra=[s["rewritten"]] if s.get("rewritten") else None) if pol else []  # #4
        return {"pol": {**pol, "chunks": chunks} if pol else None, "chunks": chunks}

    def ai_review(s):
        case, docs = case_and_docs(s)
        raw = eng.review(case, docs, s.get("pol"), session=session, actor=s["actor"], feedback=s.get("feedback"))
        if eng.label == "AI-MK":
            from app.llm import client as llm
            llm.record(session, purpose="review", engine="AI-MK", model="AI-MK", case_id=case.id, actor=s["actor"])
        try:
            result = ReviewResult.model_validate(raw)
        except ValidationError:
            raw = eng.review(case, docs, s.get("pol"), session=session, actor=s["actor"], feedback=s.get("feedback"))
            try:
                result = ReviewResult.model_validate(raw)
            except ValidationError as e:
                raise AppError(f"{eng.label} returned an invalid review: {e.error_count()} problem(s)")
        return {"result": result.model_dump(), "attempts": s.get("attempts", 0) + 1}

    def verify(s):
        case, docs = case_and_docs(s)
        pol = s.get("pol")
        pol_pdf = policy.policy_path(pol["cpt"])[0] if pol else None
        result = rv.verify(ReviewResult.model_validate(s["result"]), docs, pol_pdf, s.get("cpt_read"))
        result = rv.guard_check(result, docs)                # F22
        failed = [w for w in result.warnings if w.startswith(("Quote not found", "Policy quote not found",
                                                                 "CPT mismatch"))]
        return {"result": result.model_dump(), "feedback": "\n".join(failed) or None}

    def route(s):
        case, _ = case_and_docs(s)
        r = rv.save_review(session, case, eng, ReviewResult.model_validate(s["result"]), s.get("pol"),
                           s.get("chunks", []), s["actor"], pipeline="graph",
                           steps=s.get("steps", []) + [{"node": "route", "ms": 0}], rewritten=s.get("rewritten"))
        return {"review_id": r.id}

    def after_verify(s) -> str:
        if not s.get("feedback") or eng.label == "AI-MK" or s.get("attempts", 0) >= MAX_ATTEMPTS:
            return "route"
        from app.llm import client as llm
        if llm.totals(session, case_id=s["case_id"])["cost_usd"] >= settings.max_case_cost_usd:
            return "route"
        return "ai_review"

    g = StateGraph(ReviewState)
    g.add_node("read_form", _timed("read_form", read_form))
    g.add_node("rewrite_query", _timed("rewrite_query", rewrite_query))
    g.add_node("retrieve_policy", _timed("retrieve_policy", retrieve_policy))
    g.add_node("ai_review", _timed("ai_review", ai_review))
    g.add_node("verify", _timed("verify", verify))
    g.add_node("route", route)
    g.add_edge(START, "read_form")
    g.add_edge("read_form", "rewrite_query")
    g.add_edge("rewrite_query", "retrieve_policy")
    g.add_edge("retrieve_policy", "ai_review")
    g.add_edge("ai_review", "verify")
    g.add_conditional_edges("verify", after_verify, {"ai_review": "ai_review", "route": "route"})
    g.add_edge("route", END)
    return g.compile()


def run(session: Session, case_id: int, actor: str = "system"):
    if repo.get_case(session, case_id) is None:
        raise NotFound(f"Case {case_id} not found")
    from app.models import AIReview, utcnow
    from app.services import observability
    since = utcnow()
    out = build(session).invoke({"case_id": case_id, "actor": actor, "attempts": 0, "steps": []},
                                config={"recursion_limit": STEP_CAP,
                                        **tracing.run_config("case-review", llm.current_model(session))})  # F9
    r = session.get(AIReview, out["review_id"])
    observability.record_trace(session, kind="review", case_id=case_id, actor=actor, engine=r.result.get("engine"),
                               steps=r.result["pipeline"]["steps"], since=since, outcome=r.tier)
    return r
