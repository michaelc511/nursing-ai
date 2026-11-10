"""Phase 5: LangGraph review (F13/F13.1) + frozen linear baseline (F12.1). Fake Claude, no network."""
import shutil
from pathlib import Path

import pytest

from app.llm import client as llm
from app.schemas.review import ReviewResult
from tests.test_phase4 import SAMPLES, fake_client, ok_resp


def _result(quote="this quote is not in the pdf"):
    return ReviewResult.model_validate({
        "fields": {"cpt": "72148"}, "complete": True, "tier": "likely_approve", "summary": "s",
        "criteria": [{"criterion": "6 weeks of PT", "result": "met",
                      "request_evidence": [{"quote": quote, "doc": 0, "page": 1}]}]})


@pytest.fixture
def claude(monkeypatch, env):
    monkeypatch.setenv("AI_MODE", "claude")
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "72148_a_complete.pdf", env / "inbox")
    yield
    llm.set_client(None)


def _case(session):
    from app.services import intake
    return intake.poll_inbox(session, actor="test")[0]


def test_graph_runs_all_nodes_and_saves_steps(session, env):
    from app.services import review
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "72148_a_complete.pdf", env / "inbox")
    r = review.review_case(session, _case(session).id, actor="test")
    p = r.result["pipeline"]
    assert p["name"] == "graph"
    assert [s["node"] for s in p["steps"]] == ["read_form", "rewrite_query", "retrieve_policy", "ai_review", "verify", "route"]


def test_failed_quote_retries_claude_once_with_feedback(session, claude):
    from app.services import review
    msgs = fake_client(ok_resp(_result()), ok_resp(_result()))
    r = review.review_case(session, _case(session).id, actor="test")
    assert len(msgs.calls) == 2
    retry_text = msgs.calls[1]["messages"][0]["content"][-1]["text"]
    assert "<code_check_failures>" in retry_text and "Quote not found" in retry_text
    assert r.tier == "needs_review"                       # still failing after the retry -> a person checks
    assert [s["node"] for s in r.result["pipeline"]["steps"]].count("ai_review") == 2


def test_no_retry_when_case_cost_cap_reached(session, claude, monkeypatch):
    from app.services import review
    monkeypatch.setenv("MAX_CASE_COST_USD", "0.0001")
    msgs = fake_client(ok_resp(_result()))
    r = review.review_case(session, _case(session).id, actor="test")
    assert len(msgs.calls) == 1 and r.tier == "needs_review"


def test_no_retry_when_quotes_verify(session, claude):
    from app.services import review
    from app.services.review import pdf_pages
    page1 = pdf_pages(SAMPLES / "72148_a_complete.pdf")[0]
    good = page1.split("cpt")[0][:40].strip() or page1[:40]
    msgs = fake_client(ok_resp(_result(quote=good)))
    review.review_case(session, _case(session).id, actor="test")
    assert len(msgs.calls) == 1


def test_linear_baseline_still_works(session, env, monkeypatch):
    from app.services import review
    monkeypatch.setenv("REVIEW_PIPELINE", "linear")
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "72148_a_complete.pdf", env / "inbox")
    r = review.review_case(session, _case(session).id, actor="test")
    assert r.result["pipeline"]["name"] == "linear"


def test_graph_and_baseline_agree_on_the_demo_cases(session, env, monkeypatch):
    """F12.1 side-by-side: same tier and status for the 3 demo requests on AI-MK."""
    from app.services import intake, review
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    out = {}
    for pipe in ("linear", "graph"):
        monkeypatch.setenv("REVIEW_PIPELINE", pipe)
        for f in ("72148_a_complete.pdf", "73721_b_missing_pt.pdf", "70551_c_not_met.pdf"):
            shutil.copy(SAMPLES / f, env / "inbox")
            c = intake.poll_inbox(session, actor="test")[0]
            r = review.review_case(session, c.id, actor="test")
            out.setdefault(f, []).append((r.tier, c.status))
    assert all(a == b for a, b in out.values()), out
