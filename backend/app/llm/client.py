"""Claude calls with usage accounting (F6), model choice (F2), cache + fallback (N3)."""
import hashlib
import json
import os
import time
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.llm import pricing
from app.models import LLMCache, LLMCall, Setting

T = TypeVar("T", bound=BaseModel)
MODEL_KEY = "claude_model"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMUnavailable(Exception):
    """Every model failed or refused. Callers route the work to a person."""


def has_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()          # key from env; never logged
    return _client


def set_client(c) -> None:
    """Tests inject a fake client."""
    global _client
    _client = c


# ---------------------------------------------------------------- F2 model selector

def current_model(session: Session | None = None) -> str:
    if settings.demo_mode and session is not None:
        row = session.get(Setting, MODEL_KEY)
        if row and row.value in settings.claude_models:
            return row.value
    return settings.claude_model


def set_model(session: Session, model: str, actor: str) -> str:
    from app.errors import AppError, Forbidden
    from app.services import audit
    if not settings.demo_mode:
        raise Forbidden("The model selector is only available in demo mode")
    if model not in settings.claude_models:
        raise AppError(f"Pick one of: {', '.join(settings.claude_models)}")
    old = current_model(session)
    row = session.get(Setting, MODEL_KEY)
    if row:
        row.value = model
    else:
        session.add(Setting(key=MODEL_KEY, value=model))
    audit.log(session, actor, "model_changed", None, **{"from": old, "to": model})
    return model


# ---------------------------------------------------------------- F6 accounting

def record(session: Session, *, purpose: str, engine: str, model: str, usage=None, latency_ms: int = 0,
           case_id: int | None = None, cached: bool = False, status: str = "ok", actor: str | None = None) -> LLMCall:
    it = getattr(usage, "input_tokens", 0) or 0
    ot = getattr(usage, "output_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    row = LLMCall(case_id=case_id, purpose=purpose, engine=engine, model=model, input_tokens=it + cw,
                  output_tokens=ot, cache_read_tokens=cr, latency_ms=latency_ms, cached=cached, status=status,
                  cost_usd=0.0 if (cached or engine == "AI-MK") else pricing.cost(model, it, ot, cr, cw), actor=actor)
    session.add(row)
    session.flush()
    return row


def totals(session: Session, case_id: int | None = None, since=None) -> dict:
    q = select(func.count(LLMCall.id), func.coalesce(func.sum(LLMCall.input_tokens), 0),
               func.coalesce(func.sum(LLMCall.output_tokens), 0), func.coalesce(func.sum(LLMCall.cost_usd), 0.0),
               func.coalesce(func.avg(LLMCall.latency_ms), 0))
    if case_id is not None:
        q = q.where(LLMCall.case_id == case_id)
    if since is not None:
        q = q.where(LLMCall.at >= since)
    n, i, o, c, lat = session.execute(q).one()
    return {"calls": n, "input_tokens": int(i), "output_tokens": int(o), "cost_usd": round(float(c), 4),
            "avg_latency_ms": int(lat)}


# ---------------------------------------------------------------- N3 cache

def cache_key(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()


def cache_get(session: Session, key: str) -> dict | None:
    if not settings.llm_cache:
        return None
    row = session.get(LLMCache, key)
    return row.value if row else None


def cache_put(session: Session, key: str, purpose: str, model: str, value: dict) -> None:
    if settings.llm_cache and session.get(LLMCache, key) is None:
        session.add(LLMCache(key=key, purpose=purpose, model=model, value=value))


# ---------------------------------------------------------------- calls

def _models(session: Session | None, model: str | None = None) -> list[str]:
    if model:
        return [model]
    main = current_model(session)
    fb = settings.claude_fallback_model
    return [main] + ([fb] if fb and fb != main else [])


def parse(session: Session, *, purpose: str, system: str, content: list, schema: type[T], case_id: int | None = None,
          actor: str | None = None, effort: str | None = None, max_tokens: int = 16000, cache_parts=None,
          model: str | None = None) -> T:
    """Structured output validated by Pydantic. Tries the main model, then the fallback model."""
    import anthropic
    key = cache_key(purpose, system, cache_parts, schema.__name__) if cache_parts is not None else None
    if key:
        hit = cache_get(session, key)
        if hit is not None:
            record(session, purpose=purpose, engine="AI", model=hit.get("_model", "cache"), case_id=case_id,
                   cached=True, actor=actor)
            return schema.model_validate({k: v for k, v in hit.items() if k != "_model"})
    last_err = None
    for i, model in enumerate(_models(session, model)):
        t0 = time.monotonic()
        try:
            resp = client().beta.messages.parse(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": content}],
                output_format=schema, output_config={"effort": effort or settings.claude_effort},
                cache_control={"type": "ephemeral"},
                betas=[FALLBACK_BETA], fallbacks="default",
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError,
                anthropic.APITimeoutError) as e:      # retryable: try the next model
            last_err = e
            record(session, purpose=purpose, engine="AI", model=model, case_id=case_id, status="error",
                   latency_ms=int((time.monotonic() - t0) * 1000), actor=actor)
            continue
        latency = int((time.monotonic() - t0) * 1000)
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            record(session, purpose=purpose, engine="AI", model=model, usage=resp.usage, latency_ms=latency,
                   case_id=case_id, status="refused", actor=actor)
            last_err = LLMUnavailable(f"{model} returned no usable answer ({resp.stop_reason})")
            continue
        record(session, purpose=purpose, engine="AI", model=resp.model or model, usage=resp.usage,
               latency_ms=latency, case_id=case_id, status="fallback" if i else "ok", actor=actor)
        out = resp.parsed_output
        if key:
            cache_put(session, key, purpose, model, {**out.model_dump(), "_model": model})
        return out
    raise LLMUnavailable(f"AI unavailable: {last_err}")


def text(session: Session, *, purpose: str, system: str, messages: list, case_id: int | None = None,
         actor: str | None = None, effort: str = "low", max_tokens: int = 4000) -> str:
    """Plain text answer (query rewrite, chat). Same fallback + accounting as parse()."""
    import anthropic
    last_err = None
    for i, model in enumerate(_models(session)):
        t0 = time.monotonic()
        try:
            resp = client().beta.messages.create(
                model=model, max_tokens=max_tokens, system=system, messages=messages,
                output_config={"effort": effort}, betas=[FALLBACK_BETA], fallbacks="default")
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError,
                anthropic.APITimeoutError) as e:
            last_err = e
            record(session, purpose=purpose, engine="AI", model=model, case_id=case_id, status="error", actor=actor)
            continue
        latency = int((time.monotonic() - t0) * 1000)
        if resp.stop_reason == "refusal":
            record(session, purpose=purpose, engine="AI", model=model, usage=resp.usage, latency_ms=latency,
                   case_id=case_id, status="refused", actor=actor)
            last_err = LLMUnavailable("refused")
            continue
        record(session, purpose=purpose, engine="AI", model=resp.model or model, usage=resp.usage,
               latency_ms=latency, case_id=case_id, status="fallback" if i else "ok", actor=actor)
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    raise LLMUnavailable(f"AI unavailable: {last_err}")


def create(session: Session, *, purpose: str, system: str, messages: list, tools: list | None = None,
           case_id: int | None = None, actor: str | None = None, effort: str = "medium", max_tokens: int = 8000):
    """Raw response (for tool-use loops). Same accounting + fallback model as parse()."""
    import anthropic
    last_err = None
    for i, model in enumerate(_models(session)):
        t0 = time.monotonic()
        try:
            kw = {"tools": tools} if tools else {}
            resp = client().beta.messages.create(
                model=model, max_tokens=max_tokens, system=system, messages=messages,
                output_config={"effort": effort}, betas=[FALLBACK_BETA], fallbacks="default", **kw)
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError,
                anthropic.APITimeoutError) as e:
            last_err = e
            record(session, purpose=purpose, engine="AI", model=model, case_id=case_id, status="error", actor=actor)
            continue
        latency = int((time.monotonic() - t0) * 1000)
        status = "refused" if resp.stop_reason == "refusal" else ("fallback" if i else "ok")
        record(session, purpose=purpose, engine="AI", model=resp.model or model, usage=resp.usage,
               latency_ms=latency, case_id=case_id, status=status, actor=actor)
        if resp.stop_reason == "refusal":
            last_err = LLMUnavailable("refused")
            continue
        return resp
    raise LLMUnavailable(f"AI unavailable: {last_err}")
