# Dev Phase 1 prompt — paste into Claude Code

Read CLAUDE.md. Build Dev Phase 1: service layer + REST API + CLI + React UI.
Do NOT build the MCP server yet, but keep services/ ready for it.

Build in this order, and confirm the plan and file layout with me before
writing code. After each step, run the tests and show me how to try it.

1. Project scaffold
   - Repo layout per CLAUDE.md, pyproject/requirements, .env.example, README
   - SQLAlchemy models: cases, ai_reviews, decisions, audit_log
   - Repository layer for DB + blob (local ./storage)
   - Status state machine with enforced transitions + tests

2. Layer 1 — Intake
   - services/intake.py: create case from file, store blob, status=Received
   - REST: POST /intake/upload, POST /intake/poll
   - CLI: poll

3. Layer 3 — Policy
   - Sample policy PDFs in backend/policies/ (registry index.json), one per CPT:
     72148.pdf (MRI lumbar spine), 73721.pdf (MRI knee), 70551.pdf (MRI brain):
     criteria such as conservative therapy (PT/meds), red-flag exceptions,
     required documents checklist. Viewable/downloadable in the web UI.
   - services/policy.py: CPT lookup + RAG over policy chunks (Chroma +
     sentence-transformers)
   - CLI: index-policies

4. Layer 2 — AI review
   - Pydantic output schema per CLAUDE.md
   - Prompt in prompts/review_v1.md
   - services/review.py: load blob + policy chunks, call Claude API, validate
     JSON (retry once on invalid), store in ai_reviews, update status
   - REST: POST /cases/{id}/review
   - CLI: review <case_id>, run-all

5. Layer 4 — Decision + React UI
   - services/decision.py: human-only Approve/Deny/Pend, rationale required,
     override flag if decision disagrees with AI tier
   - REST: GET /cases, GET /cases/{id}, POST /cases/{id}/decision
   - React: queue (filter by status/tier), case detail (extracted fields,
     missing items, criteria with citations, tier, draft provider request),
     decision buttons with rationale; header with metrics from CLAUDE.md

6. Layer 5 — Sync (mocked)
   - services/sync.py: mock UM push + mock provider notification, write sync
     status back, Approved/Denied -> Synced
   - Incomplete cases: "send" drafted provider request via mock notifier
   - CLI: status, stuck --days N

7. Demo data
   - 3 synthetic fax-style PDFs in data/samples/:
     a) 72148 lumbar MRI, complete, meets criteria (likely_approve) — fax
     b) 73721 knee MRI, missing PT notes (Incomplete) — provider portal
     c) 70551 brain MRI, headache with no red flags (likely_deny -> needs human review) — provider upload
   - Script to copy samples into ./inbox

Done when: `python -m app.cli run-all` processes all 3 samples, and I can
open the React UI, see the queue, review case details with citations, and
approve/deny/pend with the audit log updated.
