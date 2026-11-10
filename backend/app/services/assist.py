"""Phase 6: AI Assist on Claude (F13.2 agentic RAG, F7/F16 memory, F19 gate, F22 checks, S8 hook).

LangGraph:  gate --(blocked)--> finish
               \\--> agent (tools: case lookup, policy RAG, guide RAG, stuck, metrics) --> check --> finish
- gate: injection + off-topic checks in code (no LLM call).
- agent: Claude with read-only tools that call services/ (never SQL, never decisions). AI-MK mode
  (no key / AI_MODE=mock) routes with rules and answers from the same tools, labeled AI-MK.
- check: output leak check + grounding (no sources -> "I don't know" note).
- Memory: LangGraph SqliteSaver checkpointer, one thread per user + case ("nurse1:case-3"); the last
  ASSIST_TURNS turns go to Claude; survives restarts; clear() deletes the thread.
"""
import json
import operator
import re
import sqlite3
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app import guard
from app.config import settings
from app.llm import client as llm
from app.prompts import load
from app.services import cases, policy

MAX_TOOL_ROUNDS = 4


class AssistState(TypedDict, total=False):
    question: str
    case_id: int | None
    user: str
    history: Annotated[list, operator.add]       # persisted turns: {"role", "text"}
    answer: str
    sources: list
    blocked: str | None
    engine: str
    rewritten: str | None
    tools_used: list


# ---------------------------------------------------------------- tools (read-only, over services/)

TOOLS = [
    {"name": "get_case", "description": "One case: status, document ID, AI tier, summary, missing items, criteria results.",
     "input_schema": {"type": "object", "properties": {"case_id": {"type": "integer"}}, "required": ["case_id"]}},
    {"name": "list_cases", "description": "List cases, optionally filtered by status (Received, Incomplete, ReadyForReview, Approved, Denied, Pended, Synced).",
     "input_schema": {"type": "object", "properties": {"status": {"type": "string"}}}},
    {"name": "stuck_cases", "description": "Cases stuck in the same status for more than N days.",
     "input_schema": {"type": "object", "properties": {"days": {"type": "number"}}}},
    {"name": "metrics", "description": "Turnaround, Incomplete (rework) rate, cases reviewed, override rate.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "search_policy", "description": "Search a coverage policy's criteria. cpt: 72148 lumbar spine MRI, 73721 knee MRI, 70551 brain MRI.",
     "input_schema": {"type": "object", "properties": {"question": {"type": "string"}, "cpt": {"type": "string"}},
                      "required": ["question", "cpt"]}},
    {"name": "search_guide", "description": "Search the NurseOps Now guide: terms, roles, rules, statuses, workflows, screens, FAQ.",
     "input_schema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}},
]


def _case_brief(session: Session, case_id: int) -> dict:
    d = cases.detail(session, case_id)
    res = d.get("ai_review") or {}
    return {"case_id": case_id, "doc_id": d.get("doc_id"), "status": d.get("status"), "cpt": d.get("cpt"),
            "description": d.get("description"), "ai_tier": res.get("tier"), "ai_label": d.get("ai_label"),
            "summary": res.get("summary"), "missing": [m.get("item") for m in res.get("missing") or []],
            "criteria": [{"criterion": c.get("criterion"), "result": c.get("result")} for c in res.get("criteria") or []]}


def run_tool(session: Session, name: str, args: dict, query_rewrite=None) -> tuple[object, list]:
    """Returns (result, sources)."""
    if name == "get_case":
        b = _case_brief(session, int(args["case_id"]))
        return b, [{"type": "case", "label": f"Case {b['case_id']} ({b['doc_id']})", "case_id": b["case_id"]}]
    if name == "list_cases":
        rows = cases.list_cases(session, args.get("status"), None)
        return [{k: r.get(k) for k in ("id", "doc_id", "status", "tier", "description")} for r in rows][:30], \
            [{"type": "cases", "label": "Case list"}]
    if name == "stuck_cases":
        return cases.stuck(session, float(args.get("days", 2))), [{"type": "cases", "label": "Stuck cases"}]
    if name == "metrics":
        return cases.metrics(session), [{"type": "metrics", "label": "Metrics"}]
    if name == "search_policy":
        rw = query_rewrite(args["question"]) if query_rewrite else None
        hits = policy.search(args["question"], cpt=str(args["cpt"]), k=3,
                             extra=[rw] if rw and rw != args["question"] else None)
        return [{k: h[k] for k in ("policy_number", "version", "label", "page", "quote")} for h in hits], \
            [{"type": "policy", "label": f"{h['policy_number']} v{h['version']} {h['label']}, page {h['page']}",
              "cpt": h["cpt"], "page": h["page"], "quote": h["quote"]} for h in hits[:2]]
    if name == "search_guide":
        from app.rag import index
        q = query_rewrite(args["question"]) if query_rewrite else args["question"]
        hits = index.search_guide(q, k=2)
        return hits, [{"type": "guide", "label": f"Guide {h['label']} {h['section_title']}", "quote": h["quote"]}
                      for h in hits[:1]]
    raise ValueError(f"unknown tool {name}")


# ---------------------------------------------------------------- AI-MK (no LLM) router

_BODY = {"72148": r"lumbar|back|spine|72148", "73721": r"knee|73721|menisc|ligament", "70551": r"brain|head|70551|migraine"}


def mock_answer(session: Session, q: str, case_id: int | None) -> tuple[str, list, list]:
    t = q.lower()
    m = re.search(r"case\s*#?\s*(\d+)", t)
    cid = int(m.group(1)) if m else case_id
    used, srcs = [], []
    if re.search(r"stuck", t):
        rows, s = run_tool(session, "stuck_cases", {"days": 2})
        used.append("stuck_cases"); srcs += s
        return (f"{len(rows)} case(s) stuck for more than 2 days" + (": " + ", ".join(f"Case {r.get('id')}" for r in rows)
                if rows else ".")), srcs, used
    if re.search(r"metric|turnaround|override rate|rework", t):
        mt, s = run_tool(session, "metrics", {})
        used.append("metrics"); srcs += s
        return "Current metrics: " + ", ".join(f"{k} {v}" for k, v in list(mt.items())[:5]), srcs, used
    cpt = next((c for c, rx in _BODY.items() if re.search(rx, t)), None)
    if re.search(r"polic|criteri|require|cover", t) and cpt:
        hits, s = run_tool(session, "search_policy", {"question": q, "cpt": cpt})
        used.append("search_policy"); srcs += s
        h = hits[0]
        return f"{h['policy_number']} v{h['version']} {h['label']} (page {h['page']}) says: {h['quote']}", srcs, used
    if cid and re.search(r"case|missing|status|why|tier|summary|what|next", t):
        try:
            b, s = run_tool(session, "get_case", {"case_id": cid})
        except Exception:
            return f"I don't know a case {cid}.", [], used
        used.append("get_case"); srcs += s
        miss = f" Missing: {', '.join(b['missing'])}." if b["missing"] else " Nothing is missing."
        return (f"Case {cid} ({b['doc_id']}) is {b['status']}; AI tier {b['ai_tier'] or 'not reviewed yet'}.{miss} "
                f"{b['summary'] or ''}").strip(), srcs, used
    hits, s = run_tool(session, "search_guide", {"question": q})
    used.append("search_guide"); srcs += s
    if hits and hits[0]["score"] > 0.25:
        return hits[0]["quote"][:600], srcs, used
    return "I don't know. Try asking about a case, a policy, your role or the rules.", [], used


# ---------------------------------------------------------------- Claude agent

def claude_answer(session: Session, q: str, case_id: int | None, history: list, user: str,
                  query_rewrite=None) -> tuple[str, list, list]:
    system = load("assist_v1")
    msgs = [{"role": h["role"], "content": h["text"]} for h in history[-2 * settings.assist_turns:]]
    ctx = f"(The user is looking at case {case_id}.) " if case_id else ""
    msgs.append({"role": "user", "content": f"{ctx}{q}"})
    sources, used = [], []
    for _ in range(MAX_TOOL_ROUNDS + 1):
        resp = llm.create(session, purpose="assist", system=system, messages=msgs, tools=TOOLS, case_id=case_id,
                          actor=user)
        tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        if resp.stop_reason != "tool_use" or not tool_uses:
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
            return text or "I don't know.", sources, used
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for tu in tool_uses:
            try:
                out, s = run_tool(session, tu.name, dict(tu.input), query_rewrite)
                sources += s
                used.append(tu.name)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": json.dumps(out, default=str)[:12000]})
            except Exception as e:
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": f"Error: {e}", "is_error": True})
        msgs.append({"role": "user", "content": results})
    return "I couldn't finish that within the step limit. Please ask a narrower question.", sources, used


# ---------------------------------------------------------------- graph + memory

_saver = None


def saver():
    global _saver
    if _saver is None:
        from langgraph.checkpoint.sqlite import SqliteSaver
        settings.assist_db.parent.mkdir(parents=True, exist_ok=True)
        _saver = SqliteSaver(sqlite3.connect(str(settings.assist_db), check_same_thread=False))
    return _saver


def reset_saver() -> None:
    global _saver
    _saver = None


def thread_id(user: str, case_id: int | None) -> str:
    return f"{user}:case-{case_id}" if case_id else f"{user}:general"


def build(session: Session):
    from app.services import ai_mode

    def gate(s):
        try:
            guard.check_input(s["question"])
            guard.intent_gate(s["question"])
        except guard.Blocked as b:
            return {"blocked": b.reason, "answer": b.message, "sources": [], "engine": "guard"}
        return {"blocked": None}

    def agent(s):
        from app.services import query_rewrite as qr            # S8 (Phase 7)
        seen: list[str] = []

        def rewrite(q):
            rw = qr.rewrite(session, q, s.get("case_id"), s["user"])
            if rw != q:
                seen.append(rw)
            return rw
        if ai_mode.current(session) == "claude" and llm.has_key():
            try:
                ans, src, used = claude_answer(session, s["question"], s.get("case_id"), s.get("history", []),
                                               s["user"], rewrite)
                return {"answer": ans, "sources": src, "tools_used": used, "engine": "AI",
                        "rewritten": seen[-1] if seen else None}
            except llm.LLMUnavailable:
                pass                                              # falls back to the scripted router below
        ans, src, used = mock_answer(session, s["question"], s.get("case_id"))
        return {"answer": ans, "sources": src, "tools_used": used, "engine": "AI-MK"}

    def check(s):
        try:
            guard.check_output(s["answer"], load("assist_v1"))
        except guard.Blocked as b:
            return {"answer": guard.BLOCKED_MSG, "blocked": b.reason, "sources": []}
        if not s.get("sources") and "i don't know" not in s["answer"].lower():
            return {"answer": s["answer"] + "\n\n(No source found for this answer: please check it.)"}
        return {}

    def finish(s):
        from app import pii                                      # S5: memory keeps no member names/IDs
        names = pii.case_names(session, s.get("case_id"))
        return {"history": [{"role": "user", "text": pii.redact(s["question"], names)},
                            {"role": "assistant", "text": pii.redact(s["answer"], names)}]}

    g = StateGraph(AssistState)
    g.add_node("gate", gate)
    g.add_node("agent", agent)
    g.add_node("check", check)
    g.add_node("finish", finish)
    g.add_edge(START, "gate")
    g.add_conditional_edges("gate", lambda s: "finish" if s.get("blocked") else "agent", {"finish": "finish", "agent": "agent"})
    g.add_edge("agent", "check")
    g.add_edge("check", "finish")
    g.add_edge("finish", END)
    return g.compile(checkpointer=saver())


def ask(session: Session, user: str, question: str, case_id: int | None = None) -> dict:
    from app.services import audit
    import time
    from app.models import utcnow
    from app.services import observability
    question = (question or "").strip()[:2000]
    cfg = {"configurable": {"thread_id": thread_id(user, case_id)}, "recursion_limit": 10}
    since, t0 = utcnow(), time.monotonic()
    out = build(session).invoke({"question": question, "case_id": case_id, "user": user, "answer": "",
                                 "sources": [], "blocked": None, "rewritten": None, "tools_used": []}, cfg)
    observability.record_trace(session, kind="assist", case_id=case_id, actor=user, engine=out.get("engine"),
                               steps=[{"node": "assist", "ms": int((time.monotonic() - t0) * 1000),
                                       "tools": out.get("tools_used", [])}],
                               since=since, outcome=out.get("blocked") or "answered")
    audit.log(session, user, "assist_question", case_id, engine=out.get("engine"), blocked=out.get("blocked"),
              tools=out.get("tools_used"))
    return {"answer": out["answer"], "sources": out.get("sources", []), "engine": out.get("engine"),
            "blocked": out.get("blocked"), "tools_used": out.get("tools_used", []), "rewritten": out.get("rewritten")}


def history(user: str, case_id: int | None = None) -> list:
    snap = saver().get_tuple({"configurable": {"thread_id": thread_id(user, case_id)}})
    if not snap:
        return []
    return (snap.checkpoint.get("channel_values") or {}).get("history", [])


def clear(session: Session, user: str, case_id: int | None = None) -> None:
    from app.services import audit
    saver().delete_thread(thread_id(user, case_id))
    audit.log(session, user, "assist_cleared", case_id)
