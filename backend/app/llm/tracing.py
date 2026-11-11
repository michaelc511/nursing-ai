"""F9 LangSmith tracing: Claude calls as LLM runs, search as retriever steps, tools as tool steps,
one clear run name per flow with model / prompt-version / environment tags.

Privacy (see observability.configure_langsmith): unless LANGSMITH_SHOW_CONTENT=true, LangSmith hides every
run's inputs and outputs. Metadata is NOT hidden, so:
- tokens and cost go in metadata (usage_metadata), so they still show with content hidden;
- run names, tags and metadata never carry member names, usernames, case IDs or patient text;
- the chat thread ID (user + case) is replaced in metadata by a one-way hash.
Tracing must never break a request: every helper here swallows its own errors.
"""
import hashlib
import os
from typing import Any, Callable

from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from app.llm import pricing

PROMPT_VERSIONS = {"nurse-assist": "assist_v1", "case-review": "review_v2"}  # keep in step with load("...") calls


def environment() -> str:
    return "prod" if os.environ.get("FLY_APP_NAME") else "local"       # Fly sets FLY_APP_NAME on every machine


def masked(value: str) -> str:
    """Stable, one-way label: groups a conversation in LangSmith without showing who or which case."""
    return "t-" + hashlib.sha256(value.encode()).hexdigest()[:12]


def run_config(run_name: str, model: str, thread_id: str | None = None) -> dict:
    """run_name + tags + metadata for a top-level graph call. Merge into the graph's existing config."""
    prompt = PROMPT_VERSIONS.get(run_name, "none")
    env = environment()
    metadata = {"model": model, "prompt_version": prompt, "env": env}
    if thread_id:
        metadata["thread_id"] = masked(thread_id)   # overrides LangGraph's copy of the raw configurable thread_id
    return {"run_name": run_name, "tags": [f"model:{model}", f"prompt:{prompt}", f"env:{env}"], "metadata": metadata}


# ---------------------------------------------------------------- Claude calls (item 1)

def _llm_inputs(inputs: dict) -> dict:
    """Only what a reviewer needs (shown only when content is visible); PDFs/images replaced by a placeholder."""
    kw = inputs.get("kwargs") or {}

    def _block(b):
        if isinstance(b, dict) and b.get("type") in ("document", "image"):
            return {"type": b["type"], "note": "file omitted from trace"}
        return b

    msgs = []
    for m in kw.get("messages") or []:
        c = m.get("content") if isinstance(m, dict) else None
        msgs.append({**m, "content": [_block(b) for b in c]} if isinstance(c, list) else m)
    return {"model": kw.get("model"), "system": kw.get("system"), "messages": msgs}


def _llm_outputs(resp: Any) -> dict:
    out = {"model": getattr(resp, "model", None), "stop_reason": getattr(resp, "stop_reason", None), "content": []}
    for b in getattr(resp, "content", None) or []:
        t = getattr(b, "type", "")
        if t == "text":
            out["content"].append({"type": "text", "text": getattr(b, "text", "")})
        elif t == "tool_use":
            out["content"].append({"type": "tool_use", "name": getattr(b, "name", ""), "input": getattr(b, "input", {})})
    return out


def _usage(resp: Any, model: str) -> dict:
    u = getattr(resp, "usage", None)
    it = getattr(u, "input_tokens", 0) or 0
    ot = getattr(u, "output_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    return {"input_tokens": it + cr + cw, "output_tokens": ot, "total_tokens": it + cr + cw + ot,
            "input_token_details": {"cache_read": cr, "cache_creation": cw},
            "total_cost": round(pricing.cost(model, it, ot, cr, cw), 6)}   # same price table as llm.record()


@traceable(run_type="llm", name="claude", process_inputs=_llm_inputs, process_outputs=_llm_outputs)
def _traced_call(method: Callable, purpose: str, kwargs: dict) -> Any:
    resp = method(**kwargs)
    try:
        run = get_current_run_tree()
        if run is not None:
            model = getattr(resp, "model", None) or kwargs.get("model") or "unknown"
            run.set(usage_metadata=_usage(resp, model),
                    metadata={"ls_provider": "anthropic", "ls_model_name": model, "purpose": purpose})
    except Exception:
        pass
    return resp


def llm_call(method: Callable, purpose: str, **kwargs) -> Any:
    """Call client().beta.messages.create/parse as a LangSmith LLM run. A no-op wrapper when tracing is off."""
    return _traced_call(method, purpose, kwargs, langsmith_extra={"name": f"claude-{purpose}"})


# ---------------------------------------------------------------- search + tools (item 2)

def _search_outputs(hits: Any) -> dict:
    hits = hits.get("output", hits) if isinstance(hits, dict) else hits
    return {"documents": [
        {"type": "Document", "page_content": h.get("quote") or h.get("text", ""),
         "metadata": {k: h.get(k) for k in ("label", "section_title", "page", "policy_number", "version", "score",
                                            "rerank") if h.get(k) is not None}}
        for h in hits or []
    ]}


def retriever(name: str) -> Callable:
    return traceable(run_type="retriever", name=name, process_outputs=_search_outputs)


def _tool_inputs(inputs: dict) -> dict:
    # never the SQLAlchemy session or the query-rewrite callable; args shown only when content is visible
    return {"tool": inputs.get("name"), "args": inputs.get("args")}


@traceable(run_type="tool", name="assist-tool", process_inputs=_tool_inputs)
def _traced_tool(fn: Callable, session: Any, name: str, args: dict, query_rewrite: Any) -> Any:
    return fn(session, name, args, query_rewrite)


def tool_call(fn: Callable, session: Any, name: str, args: dict, query_rewrite: Any = None) -> Any:
    """Run one AI Assist tool as a LangSmith tool step named tool-<name>."""
    return _traced_tool(fn, session, name, args, query_rewrite, langsmith_extra={"name": f"tool-{name}"})
