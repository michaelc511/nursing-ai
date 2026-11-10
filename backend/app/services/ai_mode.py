"""Which AI engine runs: AI-MK (mock) or Claude.

Default comes from AI_MODE in .env. In demo mode, staff can switch it at runtime from the header
(stored in the settings table, audited). Claude can only be chosen once the Claude engine is built
and an API key is configured. Production: DEMO_MODE off -> the switch is disabled, AI_MODE rules.
"""
import os

from sqlalchemy.orm import Session

from app.config import settings
from app.db import new_session
from app.errors import AppError, Forbidden
from app.models import Setting

MODES = {"mock", "claude"}
KEY = "ai_mode"


def claude_available() -> bool:
    from app.services.review import ClaudeEngine
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    return ClaudeEngine.ready and has_key


def _override(session: Session | None = None) -> str | None:
    if not settings.demo_mode:
        return None
    own = session is None
    s = session or new_session()
    try:
        row = s.get(Setting, KEY)
        return row.value if row and row.value in MODES else None
    except Exception:
        return None
    finally:
        if own:
            s.close()


def current(session: Session | None = None) -> str:
    return _override(session) or (settings.ai_mode if settings.ai_mode in MODES else "mock")


def set_mode(session: Session, mode: str, actor: str) -> str:
    if not settings.demo_mode:
        raise Forbidden("The AI mode switch is only available in demo mode")
    if mode not in MODES:
        raise AppError("Use mock or claude")
    if mode == "claude" and not claude_available():
        raise AppError("Claude is not connected yet (needs the Claude engine and ANTHROPIC_API_KEY)")
    old = current(session)
    row = session.get(Setting, KEY)
    if row:
        row.value = mode
    else:
        session.add(Setting(key=KEY, value=mode))
    from app.services import audit
    audit.log(session, actor, "ai_mode_changed", None, **{"from": old, "to": mode})
    return mode
