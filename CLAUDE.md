# Prior Authorization AI Prototype

## Business problem
Regional health plan, ~15,000 prior auth requests/month.
- Nurses manually review requests
- Clinical docs arrive via fax, PDF, portal, provider uploads
- Avg turnaround: 4.2 days
- 22% require rework due to missing information
- Providers frequently call for status updates

## Goal
Reduce turnaround 40% (4.2 -> ~2.5 days) with no added headcount,
while maintaining clinical quality and regulatory compliance.

## How AI helps
1. Intake + completeness check: extract data, flag missing docs at intake,
   draft provider request immediately (targets the 22% rework)
2. Nurse copilot: compare docs to policy criteria, cited summary, tier
3. Status visibility: case status always queryable (reduces provider calls)

## Non-negotiables
- AI never denies. Only a human nurse/medical director sets Approved/Denied.
  Enforce in the service layer, not the UI.
- Every AI claim cites source document (page + quote).
- Full audit trail: AI output, human decision, override flag, actor, timestamp.
- Synthetic data only in this prototype. No real PHI.
- Design for HIPAA in production (encryption, access control, BAA).

## Architecture principles
- Service layer is thick: ALL business logic lives in backend/services/.
- Clients are thin and call the same service functions:
  - REST (FastAPI) -> React web UI
  - CLI (Typer) -> local runs, cron
  - MCP server (Dev Phase 2) -> Claude Cowork scheduled trigger
- MCP and REST are adapters over services/. MCP must NOT call REST.
- Swappable storage via repository layer: SQLite + local folder now;
  Postgres + S3/Azure Blob later.
- Claude output is structured JSON validated by Pydantic. That schema is the
  contract between AI and code.
- Prompts are versioned files in backend/prompts/, not inline strings.

## Layers
Build status and run order (7 build layers incl. policy RAG and Cowork): README → How it works.

1. Intake & storage (patient docs only)
   - Raw file (fax/PDF/image) stored whole in blob storage (./storage now)
   - SQL row: case_id, source, received_at, status=Received, blob_path (pointer)
   - No RAG on patient docs
2. AI review (Claude API)
   - Reads whole case file from blob + policy criteria from Layer 3
   - Returns structured JSON: extracted fields (patient, CPT, ICD-10, provider),
     completeness + missing items, criteria met/not met with citations
     (page + quote), recommended tier (likely_approve / needs_review /
     likely_deny), draft provider request if incomplete
   - JSON stored in SQL (JSON column); status -> Incomplete or ReadyForReview
3. Policy knowledge (policies only, never patient docs)
   - Policies are PDFs (lumbar 72148, knee 73721, brain 70551), viewable/downloadable in the UI
   - CPT code lookup selects the policy
   - RAG retrieves relevant criteria chunks within that policy
   - Embeddings: sentence-transformers (Claude does not embed)
   - Vector store: Chroma now; pgvector later
   - Policies versioned; re-embed on add/update
4. Nurse decision (React UI, thin)
   - Queue view, case detail, AI summary + citations + tier
   - Approve / Deny / Pend with required rationale
   - Decision + override flag (nurse disagreed with AI tier) written to SQL
5. Systems of record sync (mocked)
   - Push decision to mock UM platform + mock provider notification
   - Incomplete cases: send drafted provider request via mock notification
   - Sync status written back to SQL; visible in Layer 4

## Case status state machine
Received -> Incomplete | ReadyForReview
Incomplete -> Received (new docs arrive)
ReadyForReview -> Approved | Denied | Pended   (human only)
Pended -> ReadyForReview
Approved | Denied -> Synced
Enforce allowed transitions in services/. Reject anything else.

## Data flow
Intake -> blob (file) + SQL (row w/ blob_path)
-> Claude reads blob + RAG policy chunks -> JSON results to SQL
-> Nurse reviews in React -> decision to SQL
-> Sync to UM/provider -> status back to SQL -> visible in React

## Tech stack
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy
- DB: SQLite (prototype) -> Postgres (prod)
- Blob: local ./storage folder (prototype) -> S3/Azure Blob (prod)
- AI: Anthropic Claude API via `anthropic` SDK
  (ANTHROPIC_API_KEY and CLAUDE_MODEL from env vars)
- PDF/image handling: send PDFs/images directly to Claude (native PDF + vision)
- RAG: Chroma + sentence-transformers (prototype) -> pgvector (prod)
- CLI: Typer, thin wrapper over services/
- Frontend: React + Vite + TypeScript
- Tests: pytest
- Dev Phase 2: MCP server (FastMCP) over services/, remote HTTPS deploy

## CLI commands
- `python -m app.cli poll`               # intake: scan ./inbox, create cases
- `python -m app.cli review <case_id>`   # AI review one case
- `python -m app.cli run-all`            # poll + review all new cases
- `python -m app.cli status`             # case counts by status
- `python -m app.cli stuck --days 2`     # cases stuck in a status > N days
- `python -m app.cli index-policies`     # (re)embed policies into Chroma

## Repo layout
backend/
  app/
    api/          # thin REST routes
    cli.py        # thin Typer CLI
    mcp_server.py # (Dev Phase 2) thin MCP adapter
    services/     # ALL business logic: intake, review, policy, decision, sync
    repositories/ # DB + blob access (swappable)
    schemas/      # Pydantic models, incl. Claude JSON output schema
    prompts/      # versioned Claude prompts
    models.py     # SQLAlchemy models (cases, ai_reviews, decisions, audit_log)
  policies/       # policy PDFs keyed by CPT (72148.pdf, 73721.pdf, 70551.pdf) + index.json
  tests/
frontend/
  src/
inbox/            # drop synthetic faxes here for `poll`
storage/          # blob stand-in
data/samples/     # synthetic request PDFs (lumbar, knee, brain) + manifest.json

## Success metrics (track in DB, show in UI header)
Turnaround time, rework % (Incomplete rate), cases reviewed, 
nurse-AI agreement / override rate.

## Coding rules
- Keep routes, CLI commands, and MCP tools to a few lines each: parse input,
  call a service, return result.
- Every service function that changes state writes an audit_log row.
- No secrets in code. Use .env + .env.example.
- Write tests for services and state transitions before UI polish.

## Project (playbook)
- App name: **NurseOps Now** — AI-assisted prior authorization for a regional health plan
  (requirements in [README.md](README.md); copy in `docs/requirements.md`).
- Stack: React (Vite + TS) · FastAPI + Typer CLI · SQLite · Claude (anthropic SDK) · RAG
  (Chroma + sentence-transformers) · deploy Docker/Fly.io.
- Naming: "Dev Phase 1/2/3" = Mike's build stages (PROMPT_DEVPHASE*.md); "Phase N" = playbook
  phases in `.scaffold_state.json`.
- Commands (from `backend/`): `python -m app.cli <cmd>`, `uvicorn app.main:app --reload`,
  `pytest`. Frontend (from `frontend/`): `npm install`, `npm run dev`, `npx vitest run`.
- Docs: `docs/architecture.md` and `docs/requirements.md` are the source; regenerate
  `docs/*.html` whenever they change (`python tools/scripts/md_to_html.py`).

## Git and authorship
- Author is Mike Chang. No `Co-Authored-By` trailer or any Claude/AI attribution in commits,
  PRs or files.
- Never commit secrets (`.env`, `secrets/`).
- `ship`: run tests (stop if any fail) → if on `main`, branch first (`feature/...`) → commit
  only files this task touched → merge into `main` with `--no-ff`
  (`Merge branch '<branch>'`) → push `main`. Report commit hashes and push result.

## Session log (memory)
- Keep one project memory named `session-log` (file `session-log.md` in this project's
  memory folder, with a pointer line in MEMORY.md).
- After finishing each task, and before ending a session, add one dated line at the top of the
  log: `- YYYY-MM-DD: <what we did> (<key files>) — next: <open item or "none">`.
- Use absolute dates, newest first. One line per task; no secrets, keys or `.env` values.
- At the start of a session, read the log's top 5 lines to pick up where we left off.
- A retro (Phase 12, full or pause) adds a line too: `- YYYY-MM-DD HH:MM: retro (<type>, after
  Phase <n>) (docs/retro/<date>.md) — next: <top improvement or next phase>`.

## Scaffold state (phases)
- `.scaffold_state.json` in the project root holds the phase progress and every answer. Read it
  at session start and before any `phase <n>` or `resume`; it overrides memory of the chat.
- Phase steps live in `/Users/mike/projects/claude-config/NEWPROJECT.md` ("Phases 3–12").
- Update the file after every phase confirm (Build or Don't build). Never put secrets in it.
