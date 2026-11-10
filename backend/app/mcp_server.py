"""Dev Phase 2 / F8: MCP server (FastMCP), a thin adapter over services/ (never calls REST).

Tools per PROMPT_DEVPHASE2_MCP.md. NO tool can set Approved/Denied/Pended: decisions stay
human-only in the web UI (the services enforce it too). Every call runs as actor "cowork".

Transport: Streamable HTTP, mounted by app.main at /mcp, guarded by a bearer token (MCP_TOKEN).
Local: `python -m app.mcp_server` runs it over stdio for MCP Inspector / Claude Desktop.
"""
from contextlib import contextmanager

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.db import init_db, new_session
from app.services import cases, intake, review

ACTOR = "cowork"
# DNS-rebinding protection stays on; list the public host here when deployed (e.g. nurseops.fly.dev).
_HOSTS = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*,testserver").split(",")
          if h.strip()]

mcp = FastMCP(
    "nurseops-now",
    instructions=("Prior authorization operator for NurseOps Now. Start runs, review new requests, report "
                  "what needs people. You cannot approve, pend or deny: only nurses and the medical director "
                  "decide, in the web app."),
    stateless_http=True, json_response=True, streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=_HOSTS,
                                                 allowed_origins=[f"https://{h}" for h in _HOSTS]),
)


@contextmanager
def _session():
    init_db()
    s = new_session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@mcp.tool()
def run_all() -> dict:
    """Check the inbox for new prior-auth requests, AI-review every new case, and return a summary:
    how many are new, which are Incomplete (and what is missing), Ready cases by AI tier, and stuck cases.
    Use this for the scheduled run."""
    with _session() as s:
        return review.run_all(s, actor=ACTOR, trigger="mcp: run_all")


@mcp.tool()
def poll_intake() -> list[int]:
    """Check the inbox only (no AI review). Returns the IDs of the new cases created."""
    with _session() as s:
        return [c.id for c in intake.poll_inbox(s, actor=ACTOR)]


@mcp.tool()
def review_case(case_id: int) -> dict:
    """Run (or re-run) the AI review of one case. Returns its suggested tier, missing items and new status.
    The AI only suggests; it never decides."""
    with _session() as s:
        r = review.review_case(s, case_id, actor=ACTOR)
        return {"case_id": case_id, "tier": r.tier, "missing": [m["item"] for m in r.result.get("missing", [])],
                "status": cases.get_case(s, case_id).status, "engine": r.result.get("engine")}


@mcp.tool()
def get_cases(status: str | None = None, tier: str | None = None) -> list[dict]:
    """List cases. Optional filters: status (Received, Incomplete, ReadyForReview, Approved, Denied, Pended,
    Synced) and tier (likely_approve, needs_review, likely_deny)."""
    with _session() as s:
        return cases.list_cases(s, status, tier)


@mcp.tool()
def get_case(case_id: int) -> dict:
    """One case in full: status, extracted fields, AI summary, criteria with citations (page + quote),
    missing items, decisions and history."""
    with _session() as s:
        return cases.detail(s, case_id)


@mcp.tool()
def get_stuck_cases(days: float = 2) -> list[dict]:
    """Cases that have stayed in the same status for more than `days` days (default 2)."""
    with _session() as s:
        return cases.stuck(s, days)


@mcp.tool()
def get_metrics() -> dict:
    """Success metrics: turnaround time, Incomplete (rework) rate, cases reviewed, nurse-AI override rate."""
    with _session() as s:
        return cases.metrics(s)


if __name__ == "__main__":
    mcp.run()
