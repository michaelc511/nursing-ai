"""Phase 8: traces (F9), PII redaction (S5), limits (F21), online quality (N4), LangSmith toggle."""
import logging
import shutil

import pytest

from app import pii
from app.services import assist, observability
from tests.test_phase4 import SAMPLES


def test_redact_patterns_and_names():
    t = "Jane Q Doe DOB 03/14/1961, member ID ABC123456, call (555) 123-4567, jane@x.com, SSN 123-45-6789"
    out = pii.redact(t, ["Jane Q Doe"])
    for leak in ("Jane", "Doe", "03/14/1961", "ABC123456", "123-4567", "jane@x.com", "123-45-6789"):
        assert leak not in out, leak
    assert "MRI lumbar spine 72148" == pii.redact("MRI lumbar spine 72148")   # clinical text and CPT kept


def test_log_filter_redacts():
    rec = logging.LogRecord("app", logging.INFO, __file__, 1, "review for %s phone %s",
                            ("ABC123456", "555-123-4567"), None)
    assert pii.RedactingFilter().filter(rec)
    msg = rec.getMessage()
    assert "ABC123456" not in msg and "555-123-4567" not in msg and "[ID]" in msg


def test_review_writes_a_trace(session, env):
    from app.services import intake, review
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "72148_a_complete.pdf", env / "inbox")
    c = intake.poll_inbox(session, actor="test")[0]
    review.review_case(session, c.id, actor="nurse1")
    t = observability.traces(session, case_id=c.id)[0]
    assert t["kind"] == "review" and t["engine"] == "AI-MK" and t["llm_calls"] == 1
    assert [s["node"] for s in t["steps"]][0] == "read_form"


def test_assist_writes_a_trace_and_memory_is_redacted(session):
    assist.ask(session, "nurse1", "My member ID is ABC123456, what are the rules?")
    hist = assist.history("nurse1")
    assert "ABC123456" not in hist[0]["text"]
    assert observability.traces(session)[0]["kind"] == "assist"


def test_rate_limit_429(session, monkeypatch):
    monkeypatch.setenv("AI_CALLS_PER_MINUTE", "2")
    observability.check_ai_limits(session, "nurse1")
    observability.check_ai_limits(session, "nurse1")
    with pytest.raises(observability.RateLimited) as e:
        observability.check_ai_limits(session, "nurse1")
    assert e.value.status_code == 429
    observability.check_ai_limits(session, "nurse2")       # per user


def test_daily_cost_cap_429(session, monkeypatch):
    from app.llm import client as llm
    monkeypatch.setenv("DAILY_COST_CAP_USD", "0.01")
    llm.record(session, purpose="review", engine="AI", model="claude-opus-5-5",
               usage=type("U", (), {"input_tokens": 10000, "output_tokens": 1000})())
    session.commit()
    with pytest.raises(observability.RateLimited, match="Daily AI budget"):
        observability.check_ai_limits(session, "nurse1")


def test_api_returns_429_and_audits(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.db import new_session
    from app.main import app
    from app.models import AuditLog
    from app.services import auth
    monkeypatch.setenv("AI_CALLS_PER_MINUTE", "1")
    with TestClient(app) as c:
        s = new_session(); auth.seed_reviewers(s); s.commit(); s.close()
        h = {"Authorization": "Bearer " + c.post("/api/auth/login", json={"username": "nurse1",
                                                                           "password": "test-pass"}).json()["token"]}
        assert c.post("/api/assist/chat", headers=h, json={"message": "rules?"}).status_code == 200
        r = c.post("/api/assist/chat", headers=h, json={"message": "rules?"})
        assert r.status_code == 429
        s = new_session()
        assert s.scalars(select(AuditLog).where(AuditLog.action == "ai_limit_hit")).first() is not None
        s.close()


def test_feedback_quality_alerts_and_candidates(session):
    for i in range(5):
        observability.add_feedback(session, kind="assist", case_id=None, rating=-1, actor="nurse1",
                                   question=f"call me at 555-123-4567 question {i}", comment="wrong")
    q = observability.quality(session)
    assert q["thumbs_down"] == 5 and any("thumbs down" in a for a in q["alerts"])
    cands = observability.golden_candidates(session)
    assert len(cands) == 5 and "555-123-4567" not in cands[0]["question"]


def test_langsmith_off_by_default_and_content_hidden(monkeypatch):
    import os
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert observability.configure_langsmith() is False and os.environ["LANGSMITH_TRACING"] == "false"
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_HIDE_INPUTS", raising=False)
    monkeypatch.delenv("LANGSMITH_HIDE_OUTPUTS", raising=False)
    assert observability.configure_langsmith() is True
    assert os.environ["LANGSMITH_HIDE_INPUTS"] == "true" and os.environ["LANGSMITH_HIDE_OUTPUTS"] == "true"
