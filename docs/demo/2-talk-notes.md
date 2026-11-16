# NurseOps Now talk notes

One file for an AI chat (a Claude Project) to answer questions about NurseOps Now during rehearsal, a presentation or an interview. Facts as of 2026-11-14. If this file and another doc disagree, this file and the date win.

## Instructions for the chat

Answer in 2-3 sentences, in plain business language, only from the uploaded docs. If the docs don't say, answer "Not in the docs" rather than guessing. Never invent numbers. 40% is a goal, not a measured result.

## What it is

- **NurseOps Now**: an AI prototype for prior authorization at a regional health plan, built by Mike Chang.
- **Problem**: about 15,000 requests a month, reviewed by hand from fax, PDF, portal and provider uploads; 4.2-day average turnaround; 22% need rework because something is missing; providers call for status.
- **Goal**: 40% faster (4.2 to about 2.5 days) with no added headcount, keeping clinical quality and compliance. Not yet measured on real work.
- **Deliverable** (from the brief): 3 AI opportunities, one Claude Cowork based prototype, a business-friendly extensible architecture, in a 15-minute talk.
- **Live**: https://nurseops-now.fly.dev on Fly.io, real Claude, synthetic data only (no real patients).

## The 3 AI opportunities

1. **Intake and completeness**: AI reads each request on arrival, extracts patient, CPT and ICD-10, flags missing documents and drafts the provider request. Targets the 22% rework.
2. **Nurse copilot**: compares documents to the policy criteria; every claim cites a page and quote; suggests a tier (likely approve, needs review, likely deny).
3. **Status visibility**: every case's status can be asked about (web app, Cowork), cutting provider calls.

## Rules that never change

- AI never approves or denies. Nurses approve or pend; only the medical director denies. Enforced in the service layer, not just the screen.
- Every AI claim cites the source (page and quote), and code checks each quote against the PDF text. A mismatch forces "needs review".
- Full audit trail: AI output, human decision, override flag, actor, timestamp.
- If Claude fails, the case goes to a person with a warning. Production never silently falls back to prepared answers.

## Architecture in one paragraph

All business logic lives in one Python service layer (FastAPI). Thin clients call the same services: the React web app for nurses and directors, a Typer CLI for ops and cron, and an MCP server for Claude Cowork. MCP never calls the REST API; both are adapters over the services. Claude reads and suggests; Python does every rule, check, status change and log entry; people decide. Storage is SQLite plus a file folder now, swappable for Postgres and S3 or Azure Blob. Policies are PDFs searched with RAG (Chroma, sentence-transformers, hybrid search and re-ranking), swappable for pgvector.

## Claude Cowork (the required prototype)

- Connected 2026-11-14 in the Claude desktop app as the custom connector **Prior Auth** at `https://nurseops-now.fly.dev/mcp`, protected by a bearer token.
- 7 MCP tools: `run_all`, `poll_intake`, `review_case`, `get_cases`, `get_case`, `get_stuck_cases`, `get_metrics`. There is no tool to approve, pend or deny.
- Scheduled task **Prior auth intake**: runs `run_all` (takes in new inbox requests, has Claude review each), then reports new cases, incomplete ones with what's missing, ready cases by tier and stuck cases. It can run daily; in production every 15 minutes or on an event.
- Every Cowork action is logged with the actor "cowork".
- Leaders can ask Cowork plain-English questions like "What's our override rate?" or "Which cases are stuck more than 2 days?"
- Talking point: "Cowork is the operator, not the engine. Swap Cowork for cron or an event trigger, and nothing else changes."
- 2026-11-14 test run: 3 new cases (1 likely approve, 1 likely deny, 1 incomplete missing PT notes and an X-ray report); no decisions made.

## Results (measured)

- Live evaluation on real Claude (2026-11-10): reviews 1.0, safety 1.0, retrieval 1.0, AI Assist 0.875. Retrieval hit@3 100%, hit@1 89%. RAGAS faithfulness 0.89.
- Red team: 44 attacks on real Claude, 0 got through.
- Tests: about 140 backend tests (pytest, fully mocked) and about 20 frontend tests (vitest), plus a CI eval gate.
- A full live eval run costs about $0.33; a demo reset or a Cowork run of 3 cases about $0.30.

## Known limits (be honest about these)

- AI Assist sometimes cites details its tools didn't return (a judge scored faithfulness 3/5 on one test).
- The 40% turnaround goal is not measured on real work.
- Synthetic data only. Before real patient data: HIPAA controls (encryption, access control), a BAA with the model provider, SSO and individual accounts.
- The live CI eval gate needs a GitHub secret that isn't set yet; the offline gate runs.
- The app sleeps when idle on Fly.io, so the first request is slow.

## Safety, cost and operations

- Guardrails block prompt injection before the model is called; PII is redacted from logs, traces and chat history.
- Login per role, 24-hour lockout per network address after 3 wrong passwords, per-user rate limits, a cost cap per case and a daily cap.
- Tracing in LangSmith with tokens and cost per run; online quality monitoring (thumbs up/down, override rate, unverified quotes).
- Model: Claude Opus by default, Sonnet as fallback; structured JSON output validated by Pydantic; prompts are versioned files.

## Extending it

- New policy: add a PDF and re-index.
- New intake channel: one more thin client over the same services.
- New trigger: replace Cowork with cron or an event; nothing else changes.
- Production storage: Postgres and cloud blob storage behind the same repository layer.

## Likely questions

- **Can the AI deny a request?** No. No tool, screen or service allows it; only the medical director can deny.
- **How do you know the citations are right?** Code checks every quote against the PDF text; any mismatch forces needs review.
- **What does MCP do here?** It's the standard way Claude Cowork uses the app's tools. It gives Cowork 7 tools over the same services as the web app, with no decision tool.
- **Why Cowork instead of a scheduler?** Cowork adds plain-English reporting and questions on top; the trigger is swappable, so a scheduler works too.
- **What happens if Claude is down?** The case goes to a person with a warning; nothing is decided automatically.
- **How would you measure the 40%?** Turnaround, rework rate, cases reviewed and override rate are tracked in the app and shown as tiles; measure them on real cases in a pilot.
- **What would production take?** HIPAA controls, a BAA, SSO, Postgres and cloud storage, the live CI gate, and a pilot to measure turnaround.
- **What's the cost?** About $0.10 per case review on real Claude, with per-case and daily caps.
- **What was hardest?** Making every AI claim verifiable: quotes are checked against the PDF, and the AI's output is a validated schema rather than free text.

## Where details live

- `docs/demo/1-short_script.md`: the talk, short lines per section.
- `docs/demo/4-demo-script.md`: full demo steps, commands, Cowork setup, troubleshooting.
- `docs/architecture.md`: technical design. `docs/features.md`: all features and status. `docs/governance.md`: risks and controls.
- `README.md`: requirements and build status. `cowork.md`: Cowork connector setup.
