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

## AI engines (Phase 3-4)
- `AI_MODE=mock` → **AI-MK**: prepared answers for the demo requests, same `ReviewResult` schema as Claude; every output labeled (AI-MK).
- `AI_MODE=claude` → real Claude: request PDFs sent natively + the RAG policy chunks inside `<policy_chunks>`, prompt `backend/app/prompts/review_v1.md`, structured output validated against `ReviewResult` (`client.beta.messages.parse`), effort `high`, server-side refusal fallback on.
- LLM layer `backend/app/llm/`: model from `CLAUDE_MODEL` (default `claude-opus-5-5`), allowed list `CLAUDE_MODELS`, switchable in demo mode (F2, `GET/POST /api/ai/model`); every call written to `llm_calls` with tokens, cost and latency, prompts never stored (F6, `GET /api/ai/usage`); exact-input cache in `llm_cache` and a fallback model `CLAUDE_FALLBACK_MODEL` (N3). If every model fails, the case goes to a person (Ready for review, needs review, warning "AI unavailable"); production never shows mock answers.
- Guardrails `backend/app/guard.py` (F22): instruction-like text in a document is flagged and forces needs_review; outputs that leak the prompt or a key are blocked; chat input checks + topic gate (F19) are used by AI Assist (Phase 6).
- Parsing `backend/app/services/parsing.py` (N1): text per page with local OCR (RapidOCR) for scanned faxes, so CPT regex, quote checks and the injection scan work on scans.
- MCP (F8, Dev Phase 2): `backend/app/mcp_server.py` (FastMCP) with 7 tools over services/ and no decision tool; Streamable HTTP at `/mcp`, bearer `MCP_TOKEN` (off if unset), allowed hosts `MCP_ALLOWED_HOSTS`. Local: `python -m app.mcp_server` (stdio).
- Live check (key needed, costs money): `AI_MODE=claude python ../evaluation/ask_live.py` from `backend/`.
- Either way Python reads the CPT (#2a), verifies quotes against the PDF text, and forces needs_review on any mismatch.

## Policy RAG (Phase 3, Layer 3)
- `backend/app/rag/chunker.py`: policy PDF → clause-aware chunks (S14), one per criterion (§2.A…) or section, each with a header `[policy v<version> | title | CPT | §label section | page]`; page furniture dropped; recursive split above 1,200 chars; injection-like text flagged and kept out of the index.
- `backend/app/rag/index.py`: sentence-transformers `all-MiniLM-L6-v2` (Claude never embeds) → Chroma collection `policies` in `backend/data/chroma/` (git-ignored). Metadata per chunk (S4): cpt, policy number, version, section, criterion, page.
- Search is always filtered to the CPT's policy. Re-index replaces a policy's old chunks (N2: versioned). The index builds itself on first search.
- The AI review gets the top 6 chunks of the case's policy and saves them with the review (`policy_chunks`), so every citation can point to its clause.
- CLI `index-policies`, `search-policies "<question>" --cpt <code>`; API `GET /api/policies/{cpt}/search?q=`, `GET /api/policies/{cpt}/chunks`.
- Retrieval eval: `evaluation/golden.jsonl` + `python ../evaluation/run_retrieval.py` (from `backend/`). Baseline 2026-11-10: hit@1 8/9 (89%); off-topic scores ≈ 0.

## Retrieval quality (Phase 7)
- Hybrid search (F18): every chunk in the CPT's policy is scored by vector cosine and by BM25 (keywords + section title), fused with Reciprocal Rank Fusion (k=60). `HYBRID_SEARCH=false` turns BM25 off.
- Re-ranking (F10): cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2` re-orders the top 10 (`RERANK=false` off). `score` stays the vector cosine (used for "I don't know"), `rerank` is the cross-encoder score.
- Query rewriting (S8): in Claude mode, `backend/app/services/query_rewrite.py` (prompt `rewrite_v1.md`, effort low) restates the chat question or the request's first page in policy wording, with personal details removed; original + rewritten results are fused. Review graph node `rewrite_query`; AI Assist shows the rewritten query (debug). AI-MK keeps the original query.
- Retrieval eval 2026-11-10 (real models): hit@1 8/9 (89%), hit@3 9/9 (100%), up from 89% hit@3 in Phase 3.

## Review pipeline (Phase 5, LangGraph)
- `backend/app/services/review_graph.py`: `read_form → rewrite_query → retrieve_policy → ai_review → verify → route`. Only `ai_review` calls the AI; the other nodes are Python (CPT regex, CPT → policy + RAG chunks, quote/CPT/injection checks, save + status move).
- `verify → ai_review` retries once (Claude only) with the failed checks as feedback, while the case is under `MAX_CASE_COST_USD` (default $0.50). Step cap 8. Still failing → needs_review for a person.
- No node can approve, pend or deny. Node timings are saved with each review (`pipeline.steps`).
- F12.1 baseline: `REVIEW_PIPELINE=linear` runs the original one-pass review (frozen); tests check both give the same tier and status on the demo cases.

## AI Assist (Phase 6)
- `backend/app/services/assist.py`, LangGraph `gate → agent → check → finish`, prompt `backend/app/prompts/assist_v1.md`.
- gate (code, no LLM): injection check (F22) + topic gate (F19) → polite refusal.
- agent (F13.2 agentic RAG): Claude picks read-only tools that call services/: `get_case`, `list_cases`, `stuck_cases`, `metrics`, `search_policy` (policy RAG), `search_guide` (RAG over `backend/knowledge/guide_me.pdf`, Chroma collection `guide`). Max 4 tool rounds. No SQL, no decisions. Without a key or with `AI_MODE=mock`, a rule router answers from the same tools (AI-MK).
- check: blocks prompt/key leaks; answers without a source get a "please check" note.
- Memory (F7, F16): LangGraph `SqliteSaver` in `backend/data/assist_memory.db` (git-ignored), one thread per user and case; last `ASSIST_TURNS` (10) turns go to Claude; survives restarts; `DELETE /api/assist/history` clears it (audited).
- API: `POST /api/assist/chat {message, case_id?}`, `GET/DELETE /api/assist/history?case_id=`.

## Observability and security (Phase 8)
- Traces (F9): `traces` table, one row per review run or AI Assist turn: node timings, LLM calls, tokens, cost, outcome. No content. `GET /api/ai/traces?case_id=`. LangSmith only with `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true`; inputs and outputs are hidden unless `LANGSMITH_SHOW_CONTENT=true` (synthetic demo only).
- PII (S5): `backend/app/pii.py` redacts SSN, dates, phone, email, member IDs, NPI, addresses and the case's member/provider names from application logs (log filter), AI Assist memory and feedback text. Case documents and the AI review stay complete (staff-only, audited).
- Limits (F21): per-user `AI_CALLS_PER_MINUTE` (20) on Check inbox, Run AI review, Re-run and AI Assist; app-wide `DAILY_COST_CAP_USD` ($10, UTC day). Over a limit → 429 with a plain message, audited (`ai_limit_hit`). Logins and roles: Phase 2.5.
- Online quality (N4): thumbs up/down (`POST /api/ai/feedback`), `GET /api/ai/quality` (thumbs, override rate, unverified-quote rate, AI-unavailable reviews, cost today vs cap, latency) with alerts; CLI `quality`; `export-feedback` writes thumbs-down items to `evaluation/candidates.jsonl` for a person to turn into golden cases.

## Demo tools (Claude, Phase 2.5)
- `mark <case_id> ready|incomplete` (test-only CLI) moves a case until AI review exists.
- Reset (needs `DEMO_MODE=true`): CLI `reset-demo --yes`, or the hidden area right after the "Now" title in the header (confirm popup). Wipes cases and reloads the 3 samples. Never exposed via MCP.

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
