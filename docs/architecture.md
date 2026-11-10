# NurseOps Now architecture

_Source: Mike's CLAUDE.md (architecture = "Mike describes it"). Items marked (Claude) are additions agreed in Phase 2.5._

## Overview
NurseOps Now helps prior authorization nurses at a regional health plan review MRI requests faster.
AI reads the clinical documents, checks completeness against policy, and prepares a cited summary.
**Only a human nurse or medical director approves or denies.** Every step is audited.

## Components
| Layer | What it does | Prototype | Production |
|---|---|---|---|
| 1. Intake & storage | Stores each fax/PDF whole; creates a case row with a pointer | `./storage` + SQLite | S3/Azure Blob + Postgres |
| 2. AI review | Claude reads the case file + policy criteria; returns validated JSON (fields, missing items, criteria with page + quote, tier, draft provider request) | Claude API (Phase 3–4) | same |
| 3. Policy knowledge | CPT code selects the policy PDF (lumbar 72148, knee 73721, brain 70551); view/download in UI now, RAG finds the criteria chunks from Phase 3 | `backend/policies/*.pdf` + Chroma (Phase 3) | pgvector |
| 4. Nurse decision | Login, queue, case detail with PDF viewer (Claude), Approve / Deny / Pend with rationale | React + FastAPI | same |
| 5. Systems of record | Pushes decisions to UM platform, notifies provider | mocked | real integrations |

**Clients are thin adapters over one service layer (`backend/app/services/`):**
REST (FastAPI) → React web UI · CLI (Typer) → ops and cron · MCP server (Dev Phase 2) → Claude Cowork.
MCP never calls REST.

## How it works (layers and run order)
Build status lives in README → How it works.

**Layers**

1. Intake and storage (Python + API + CLI)
2. AI review (Claude API + Python)
3. Policy lookup and PDFs (Python + API + React)
4. Policy RAG (Python + Chroma)
5. Nurse decision (React + API)
6. Systems of record (Python, mocked)
7. Cowork operator (Cowork + MCP)

**In the order it runs** (#n = layer above)

1. **#7** Cowork operator starts the run on a schedule
2. **#1** Intake and storage turns each new document into a case
3. **#3** Policy lookup and PDFs picks the policy by CPT
4. **#4** Policy RAG finds the criteria that matter
5. **#2** AI review reads, checks, cites and suggests
6. **#6** Systems of record sends the provider request if something is missing
7. **#7** Cowork operator reports what needs people
8. **#5** Nurse decision: Nurse approves or pends, Medical Director denies
9. **#6** Systems of record syncs the decision and notifies the provider
10. **#7** Cowork operator answers status questions (stuck cases, override rate)

## Case status state machine
```
Received -> Incomplete | ReadyForReview
Incomplete -> Received            (new docs arrive)
ReadyForReview -> Approved | Denied | Pended   (human only)
Pended -> ReadyForReview
Approved | Denied -> Synced
```
Enforced in `services/`; anything else is rejected.

## Data flow
Intake → blob (file) + SQL row (blob_path) → Claude reads blob + policy chunks → JSON to SQL →
nurse reviews in React → decision to SQL → sync to UM/provider → status back to SQL → visible in React.

## Users (Claude, Phase 2.5)
Demo logins per role: `nurse1`, `nurse2` (nurse), `meddir` (medical director), `intake1`
(intake coordinator: intake + add documents, can't decide → 403); one shared
`DEMO_PASSWORD` from `.env`. Production: SSO + role-based access (HIPAA).

## Demo tools (Claude, Phase 2.5)
- `mark <case_id> ready|incomplete` (test-only CLI) moves a case until AI review exists.
- Reset (needs `DEMO_MODE=true`): CLI `reset-demo --yes`, or the hidden area right after the "Now" title in the header (confirm popup). Wipes cases and reloads the 3 samples. Never exposed via MCP.
- Simulated AI check (demo mode, web): Check passed / Missing info on Received cases, until Phase 3.

## Built so far
- Phase 2.5 (no AI): Layers 1, 4, 5 + state machine, login, CLI, React UI with PDF viewer. 42 pytest + 2 vitest; handoff scripts W1/W2 in README.
- Code map: `backend/app/services/` (state, intake, decision, sync, cases, auth, demo, audit),
  `backend/app/repositories/` (cases, blob), `backend/app/api/routes.py`, `backend/app/cli.py`, `frontend/src/`.

## External services
- Anthropic Claude API (`ANTHROPIC_API_KEY`, `CLAUDE_MODEL`)
- Fly.io (deploy, Phase 11) · Claude Cowork via MCP custom connector (Dev Phase 3)

## Non-negotiables
AI never denies · every AI claim cites page + quote · full audit trail · synthetic data only, no PHI ·
designed for HIPAA in production (encryption, access control, BAA).
