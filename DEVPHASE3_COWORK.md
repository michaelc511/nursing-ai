# Dev Phase 3 — Claude Cowork trigger (set up in Claude, not Claude Code)

## Prerequisites
- Dev Phase 2 MCP server deployed with a public HTTPS URL
- Added as a custom connector in Claude (check that custom connectors are
  enabled on the account you will demo from)

## Scheduled task
Create a scheduled task in Claude with this prompt:

> Use the Prior Auth connector. Run run_all to process new prior auth requests.
> Then call get_metrics and get_stuck_cases with days=2.
> Report: number of new cases, how many are Incomplete (with missing items),
> how many are Ready for Review by tier, and any stuck cases.
> Do not make approval or denial decisions; those are done by nurses in the web UI.

Schedule: daily for the demo. Say in the presentation: every 15 minutes or
event-driven in production.

## Live demo script
1. Drop the 3 sample faxes into the inbox
2. In Cowork, run the scheduled task on demand (don't wait for the schedule)
3. Show Cowork's summary (new cases, incomplete, by tier)
4. Open the React nurse UI: queue, then case detail with citations
5. Approve one case, pend one; show the audit log + synced status
6. In Cowork, ask: "Which cases are stuck more than 2 days?" or "What's our override rate?"

## Talking point
"Cowork is the operator, not the engine. All logic lives in the FastAPI
service layer, exposed as REST for the web, CLI for ops, and MCP for Claude.
Swap Cowork for cron or an event trigger, and nothing else changes."
