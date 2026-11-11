"""F9 LangSmith tracing + privacy. Captures what would be sent to LangSmith (no network) and checks it:
run names and tags, LLM runs with tokens and cost, retriever and tool steps, and with content hidden
(the default) no question, answer, username or case ID leaves the app. Fake Claude, no API key."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import langsmith
import pytest

from app.llm import client as llm
from app.llm import tracing
from app.services import assist, observability
from tests.test_assist import demo_cases  # noqa: F401  (fixture)
from tests.test_phase4 import fake_client

QUESTION = "What is missing on case 2 for the lumbar MRI?"
ANSWER = "Case 2 is Incomplete: PT notes are missing."


@pytest.fixture
def captured(monkeypatch):
    """Turns LangSmith on the way the app does (configure_langsmith) and records every payload."""
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-not-real")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    for v in ("LANGSMITH_SHOW_CONTENT", "LANGSMITH_HIDE_INPUTS", "LANGSMITH_HIDE_OUTPUTS", "FLY_APP_NAME"):
        monkeypatch.delenv(v, raising=False)
    assert observability.configure_langsmith()
    client = langsmith.Client(api_key="test-not-real", api_url="http://127.0.0.1:9", auto_batch_tracing=False)
    sent: list[str] = []

    def fake_request(method, url, *a, **kw):
        body = kw.get("data") or kw.get("json")
        sent.append(body.decode() if isinstance(body, bytes) else body if isinstance(body, str) else json.dumps(body))
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {}
        return r

    client.session.request = fake_request
    with langsmith.tracing_context(enabled=True, client=client):
        yield sent


def _ask_with_tools(session, monkeypatch):
    monkeypatch.setenv("AI_MODE", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    usage = SimpleNamespace(input_tokens=900, output_tokens=60, cache_read_input_tokens=100,
                            cache_creation_input_tokens=0)
    tool_turn = SimpleNamespace(stop_reason="tool_use", model="claude-opus-5-5", usage=usage, content=[
        SimpleNamespace(type="tool_use", id="t1", name="get_case", input={"case_id": 2}),
        SimpleNamespace(type="tool_use", id="t2", name="search_policy",
                        input={"question": "conservative therapy weeks", "cpt": "72148"})])
    final = SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5", usage=usage, content=[
        SimpleNamespace(type="text", text=ANSWER)])
    rewrite = SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5", usage=usage, content=[
        SimpleNamespace(type="text", text="weeks of conservative therapy before lumbar MRI")])  # S8 query rewrite
    fake_client(tool_turn, rewrite, final)
    try:
        return assist.ask(session, "nurse1", QUESTION, case_id=2)
    finally:
        llm.set_client(None)


def test_trace_has_names_tags_usage_and_steps(session, demo_cases, captured, monkeypatch):  # noqa: F811
    r = _ask_with_tools(session, monkeypatch)
    assert r["answer"] == ANSWER
    blob = "\n".join(captured)
    assert '"nurse-assist"' in blob                                   # item 3: run name
    assert "env:local" in blob and "prompt:assist_v1" in blob and "model:" in blob
    assert '"claude-assist"' in blob and '"run_type":"llm"' in blob  # item 1: LLM runs ...
    assert '"usage_metadata"' in blob and '"total_cost"' in blob      # ... with tokens and cost in metadata
    assert '"input_tokens":1000' in blob                             # 900 + 100 cache read
    assert '"tool-get_case"' in blob and '"tool-search_policy"' in blob  # item 2: tool steps
    assert '"policy-search"' in blob and '"run_type":"retriever"' in blob


def test_content_hidden_by_default_no_phi_or_ids(session, demo_cases, captured, monkeypatch):  # noqa: F811
    _ask_with_tools(session, monkeypatch)
    blob = "\n".join(captured)
    assert blob, "nothing was traced"
    for secret in (QUESTION, ANSWER, "PT notes", "nurse1", "nurse1:case-2", "looking at case 2",
                   "conservative therapy weeks"):
        assert secret not in blob, f"{secret!r} reached LangSmith"
    assert tracing.masked("nurse1:case-2") in blob                    # thread grouped by hash only


def test_tracing_off_changes_nothing(session, demo_cases, monkeypatch):  # noqa: F811
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    assert _ask_with_tools(session, monkeypatch)["answer"] == ANSWER


def test_run_config_prod_and_masking(monkeypatch):
    monkeypatch.setenv("FLY_APP_NAME", "nurseops-now")
    cfg = tracing.run_config("case-review", "claude-opus-5-5")
    assert cfg["run_name"] == "case-review"
    assert cfg["tags"] == ["model:claude-opus-5-5", "prompt:review_v2", "env:prod"]
    assert "thread_id" not in cfg["metadata"]
    m = tracing.masked("nurse1:general")
    assert m.startswith("t-") and "nurse1" not in m and m == tracing.masked("nurse1:general")


def test_case_review_run_is_named_and_hidden(session, captured, env):
    # the review graph runs under tracing here (mock AI-MK engine): named case-review, no case content sent
    import shutil
    from app.services import review
    from tests.test_assist import SAMPLES
    shutil.copytree(SAMPLES / "mock_reviews", env / "samples" / "mock_reviews")
    shutil.copy(SAMPLES / "72148_a_complete.pdf", env / "inbox")
    review.run_all(session, actor="nurse1", trigger="test")
    blob = "\n".join(captured)
    assert '"case-review"' in blob and "prompt:review_v2" in blob
    assert "nurse1" not in blob and "72148_a_complete" not in blob
