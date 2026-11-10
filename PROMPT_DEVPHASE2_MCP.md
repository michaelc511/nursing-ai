# Dev Phase 2 prompt — paste into Claude Code (after Dev Phase 1 works)

Read CLAUDE.md. Add Dev Phase 2: an MCP server so Claude Cowork can trigger and
query the system.

1. backend/app/mcp_server.py using FastMCP
   - Thin adapter over services/ (do NOT call the REST API)
   - Tools:
     - run_all() -> poll inbox + review new cases, return summary counts
     - poll_intake() -> new case IDs
     - review_case(case_id) -> tier + missing items
     - get_cases(status?, tier?) -> list
     - get_case(case_id) -> AI summary + citations + status
     - get_stuck_cases(days) -> cases stuck in a status > N days
     - get_metrics() -> turnaround, Incomplete rate, override rate
   - NO tool may set Approved/Denied. Decisions stay human-only in the web UI.
   - Clear tool descriptions so Claude knows when to use each.

2. Remote deployment
   - Streamable HTTP transport over HTTPS
   - Simple auth (bearer token from env var)
   - Dockerfile + deploy notes for Render or Fly.io
   - Deploy FastAPI REST + React build alongside so the nurse UI is reachable

3. Tests for MCP tools (call through the adapter, assert service behavior)

4. README section: how to add this as a custom connector in Claude.

Confirm the plan before writing code.
