"""S8 query rewriting: Claude restates a vague chat question or a request's clinical text in the
policy's own wording before policy search. Results for the original and rewritten queries are fused
(RRF) in rag/index.search. Claude mode only; AI-MK keeps the original query. Personal details are
removed by the prompt and by code (simple PII patterns) before the query is logged anywhere.
"""
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.llm import client as llm
from app.prompts import load

_PII = re.compile(r"\b(\d{3}-\d{2}-\d{4}|\d{2}/\d{2}/\d{4}|[A-Z]{2,4}\d{6,}|[\w.+-]+@[\w-]+\.[\w.]+|\(?\d{3}\)?[ -]\d{3}-\d{4})\b")


def enabled(session: Session) -> bool:
    from app.services import ai_mode
    return settings.query_rewrite and ai_mode.current(session) == "claude" and llm.has_key()


def rewrite(session: Session, text: str, case_id: int | None = None, actor: str | None = None) -> str:
    """Returns the rewritten query, or the original text when rewriting is off or fails."""
    text = (text or "").strip()
    if not text or not enabled(session):
        return text
    try:
        out = llm.text(session, purpose="rewrite", system=load("rewrite_v1"),
                       messages=[{"role": "user", "content": f"<text>{text[:2000]}</text>"}],
                       case_id=case_id, actor=actor, effort="low", max_tokens=200)
    except llm.LLMUnavailable:
        return text
    out = _PII.sub("[removed]", out.strip().strip('"'))[:300]
    return out or text
