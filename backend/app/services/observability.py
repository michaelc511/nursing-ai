"""Phase 8: traces (F9), limits (F21), online quality monitoring (N4), LangSmith toggle.

- record_trace(): one row per review run / AI Assist turn (node timings + tokens + cost, no content).
- check_ai_limits(): per-user AI calls per minute + daily cost cap -> 429 (audited).
- quality(): thumbs, override rate, unverified-quote rate, cost/latency, alerts over thresholds.
- LangSmith: on only with LANGSMITH_API_KEY + LANGSMITH_TRACING=true; inputs/outputs hidden unless
  LANGSMITH_SHOW_CONTENT=true (synthetic demo only), so no PHI leaves the app by default.
"""
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models import AIReview, Decision, Feedback, LLMCall, Trace

# ---------------------------------------------------------------- LangSmith


def configure_langsmith() -> bool:
    on = bool(os.environ.get("LANGSMITH_API_KEY")) and os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
    if on and os.environ.get("LANGSMITH_SHOW_CONTENT", "").lower() != "true":
        os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
        os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")
    if not on:
        os.environ["LANGSMITH_TRACING"] = "false"
    return on


# ---------------------------------------------------------------- F9 traces

def record_trace(session: Session, *, kind: str, case_id: int | None, actor: str | None, engine: str | None,
                 steps: list, since: datetime, outcome: str | None) -> Trace:
    q = select(func.count(LLMCall.id), func.coalesce(func.sum(LLMCall.input_tokens), 0),
               func.coalesce(func.sum(LLMCall.output_tokens), 0), func.coalesce(func.sum(LLMCall.cost_usd), 0.0)
               ).where(LLMCall.at >= since, LLMCall.actor == actor)
    if case_id is not None:
        q = q.where(LLMCall.case_id == case_id)
    n, i, o, c = session.execute(q).one()
    t = Trace(kind=kind, case_id=case_id, actor=actor, engine=engine, steps=steps,
              total_ms=sum(s.get("ms", 0) for s in steps), llm_calls=n, input_tokens=int(i), output_tokens=int(o),
              cost_usd=round(float(c), 6), outcome=outcome)
    session.add(t)
    session.flush()
    return t


def traces(session: Session, case_id: int | None = None, limit: int = 20) -> list[dict]:
    q = select(Trace).order_by(Trace.id.desc()).limit(limit)
    if case_id is not None:
        q = q.where(Trace.case_id == case_id)
    return [{"id": t.id, "kind": t.kind, "case_id": t.case_id, "actor": t.actor, "engine": t.engine,
             "steps": t.steps, "total_ms": t.total_ms, "llm_calls": t.llm_calls, "input_tokens": t.input_tokens,
             "output_tokens": t.output_tokens, "cost_usd": t.cost_usd, "outcome": t.outcome,
             "at": t.at.isoformat()} for t in session.scalars(q)]


# ---------------------------------------------------------------- F21 limits

class RateLimited(AppError):
    status_code = 429


_hits: dict[str, deque] = defaultdict(deque)


def reset_limits() -> None:
    _hits.clear()


def check_ai_limits(session: Session, user: str) -> None:
    now = time.monotonic()
    q = _hits[user]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.ai_calls_per_minute:
        _audit_limit(session, user, "rate")
        raise RateLimited(f"Too many AI requests: limit {settings.ai_calls_per_minute} per minute. Try again shortly.")
    spent = daily_cost(session)
    if spent >= settings.daily_cost_cap_usd:
        _audit_limit(session, user, "daily_cost")
        raise RateLimited(f"Daily AI budget reached (${spent:.2f} of ${settings.daily_cost_cap_usd:.2f}). "
                          "AI resumes tomorrow; cases can still be reviewed by people.")
    q.append(now)


def _audit_limit(session: Session, user: str, which: str) -> None:
    """Own session: the request's session is rolled back when the 429 is raised."""
    from app.db import new_session
    from app.services import audit
    s = new_session()
    try:
        audit.log(s, user, "ai_limit_hit", None, limit=which)
        s.commit()
    finally:
        s.close()


def daily_cost(session: Session) -> float:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    return float(session.scalar(select(func.coalesce(func.sum(LLMCall.cost_usd), 0.0)).where(LLMCall.at >= start)))


# ---------------------------------------------------------------- N4 online quality

def add_feedback(session: Session, *, kind: str, case_id: int | None, rating: int, actor: str,
                 comment: str | None = None, question: str | None = None) -> Feedback:
    from app import pii
    from app.services import audit
    if kind not in {"review", "assist"} or rating not in (1, -1):
        raise AppError("kind must be review|assist and rating 1|-1")
    names = pii.case_names(session, case_id)
    fb = Feedback(kind=kind, case_id=case_id, rating=rating, actor=actor,
                  comment=pii.redact(comment, names)[:1000] if comment else None,
                  question=pii.redact(question, names)[:1000] if question else None)
    session.add(fb)
    session.flush()
    audit.log(session, actor, "ai_feedback", case_id, kind=kind, rating=rating)
    return fb


def quality(session: Session, days: int = 7) -> dict:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    fbs = session.scalars(select(Feedback).where(Feedback.at >= since)).all()
    up = sum(1 for f in fbs if f.rating > 0)
    down = len(fbs) - up
    decisions = session.scalars(select(Decision).where(Decision.created_at >= since)).all()
    override = sum(1 for d in decisions if d.override) / len(decisions) if decisions else 0.0
    reviews = session.scalars(select(AIReview).where(AIReview.created_at >= since)).all()
    unverified = sum(1 for r in reviews if any(str(w).startswith(("Quote not found", "Policy quote not found"))
                                              for w in (r.result or {}).get("warnings", []))) / len(reviews) if reviews else 0.0
    unavailable = sum(1 for r in reviews if any("AI unavailable" in str(w)
                                                for w in (r.result or {}).get("warnings", [])))
    calls = session.execute(select(func.count(LLMCall.id), func.coalesce(func.avg(LLMCall.latency_ms), 0),
                                   func.coalesce(func.sum(LLMCall.cost_usd), 0.0)).where(LLMCall.at >= since)).one()
    today = daily_cost(session)
    out = {"days": days, "thumbs_up": up, "thumbs_down": down,
           "thumbs_down_rate": round(down / len(fbs), 3) if fbs else 0.0,
           "override_rate": round(override, 3), "unverified_quote_rate": round(unverified, 3),
           "ai_unavailable_reviews": unavailable, "reviews": len(reviews), "ai_calls": calls[0],
           "avg_latency_ms": int(calls[1]), "cost_usd": round(float(calls[2]), 4),
           "cost_today_usd": round(today, 4), "daily_cap_usd": settings.daily_cost_cap_usd}
    alerts = []
    if len(fbs) >= 5 and out["thumbs_down_rate"] > 0.30:
        alerts.append("More than 30% of AI answers got a thumbs down this week.")
    if len(decisions) >= 5 and override > 0.30:
        alerts.append("Nurses overrode the AI tier on more than 30% of decisions (possible drift).")
    if len(reviews) >= 5 and unverified > 0.20:
        alerts.append("More than 20% of AI reviews had quotes that could not be verified.")
    if today >= 0.8 * settings.daily_cost_cap_usd:
        alerts.append(f"AI spend today is at {today / settings.daily_cost_cap_usd:.0%} of the daily cap.")
    if unavailable:
        alerts.append(f"{unavailable} review(s) ran without AI (AI unavailable): people reviewed them.")
    out["alerts"] = alerts
    return out


def golden_candidates(session: Session) -> list[dict]:
    """Thumbs-down items become candidate golden cases (Phase 9) for a person to review."""
    rows = session.scalars(select(Feedback).where(Feedback.rating < 0).order_by(Feedback.id)).all()
    return [{"id": f"fb{f.id}", "type": f.kind, "case_id": f.case_id, "question": f.question,
             "comment": f.comment, "source": "thumbs-down, needs a person to write the expected answer"}
            for f in rows]
