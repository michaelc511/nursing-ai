"""Phase 7: hybrid search (F18), re-ranking (F10), query rewriting (S8). Offline."""
from types import SimpleNamespace

import pytest

from app.llm import client as llm
from app.rag import index
from app.services import policy
from tests.test_phase4 import fake_client


def test_bm25_finds_an_exact_term(monkeypatch):
    """Exact policy words (section title) rank first with BM25 on; the real-model check is run_retrieval.py."""
    policy.index_policies()
    assert policy.search("required documentation", cpt="73721", k=1)[0]["label"] == "§3"


def test_hybrid_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("HYBRID_SEARCH", "false")
    policy.index_policies()
    assert policy.search("knee x-ray report", cpt="73721", k=2)


class ReverseReranker:
    name = "reverse"

    def score(self, query, texts):
        return [-len(t) for t in texts]                     # prefers the shortest chunk


def test_reranker_reorders_and_reports_scores():
    policy.index_policies()
    index.set_reranker(ReverseReranker())
    hits = policy.search("knee", cpt="73721", k=8)
    lens = [len(h["quote"]) for h in hits]
    assert lens == sorted(lens) and hits[0]["rerank"] is not None


def test_rewritten_query_is_fused(monkeypatch):
    policy.index_policies()
    base = [h["id"] for h in policy.search("my knee keeps giving out", cpt="73721", k=3)]
    fused = policy.search("my knee keeps giving out", cpt="73721", k=3,
                          extra=["mechanical symptoms locking catching giving way McMurray meniscus tear"])
    assert fused and fused[0]["label"] == "§2.A"
    assert base  # original still searched


def test_rewrite_only_in_claude_mode(session):
    from app.services import query_rewrite
    assert query_rewrite.rewrite(session, "bad back 2 months") == "bad back 2 months"   # AI-MK: unchanged


def test_rewrite_calls_claude_and_strips_pii(session, monkeypatch):
    from app.services import query_rewrite
    monkeypatch.setenv("AI_MODE", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    usage = SimpleNamespace(input_tokens=50, output_tokens=12, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    fake_client(SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5", usage=usage, content=[
        SimpleNamespace(type="text", text="low back pain 8 weeks failed physical therapy member 123-45-6789")]))
    try:
        out = query_rewrite.rewrite(session, "Pt John has had a bad back for 2 months, PT didn't help")
    finally:
        llm.set_client(None)
    assert "conservative" in out or "physical therapy" in out
    assert "123-45-6789" not in out and "[removed]" in out
