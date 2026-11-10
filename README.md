# NurseOps Now — Prior Authorization AI Prototype

## Problem statement

A regional health plan processes approximately 15,000 prior authorization requests per month.

**Current state:**

- Nurses manually review requests.
- Clinical documentation arrives through fax, PDFs, portals, and provider uploads.
- Average turnaround time is 4.2 days.
- 22% require rework because of missing information.
- Providers frequently call for status updates.

Leadership wants to reduce turnaround time by 40% without increasing headcount.

The Chief Medical Officer asks:

> "How can AI improve this process while maintaining clinical quality and regulatory compliance?"

## Deliverable (show workflow)

- Design and develop a rapid AI prototype with Claude, and present it in 15 minutes.
- Present 3 AI opportunities for the problem space above.
- Build one Claude Cowork based prototype.
- Present the architecture in a business-friendly way, showing how it can be extended.

## Features
Built so far (updated every phase):
- **Phase 2.5 App Core (no AI):** login per role (nurse1, nurse2, meddir, intake1; shared `DEMO_PASSWORD`),
  intake (inbox poll + upload), case state machine, human-only Approve/Deny/Pend with rationale,
  override flag, audit log, mocked UM sync + provider notice, queue + case detail with PDF viewer,
  Add documents for Incomplete cases, metrics header, CLI (`init-db`, `poll`, `list`, `status`, `stuck`, test-only `mark`, `reset-demo`).
- 3 synthetic MRI requests in `data/samples/`: A lumbar spine (72148), B knee (73721), C brain (70551), (`python scripts/make_samples.py`); `data/samples/manifest.json` sets each one's intake channel (A fax, B provider portal, C provider upload) and the diagnosis shown in the queue description (Claude reads these from the document from Phase 3).
- Next: Phase 3 policy + AI review (Claude).

## How it works
Python does every rule, check, status change and log entry; Claude reads and suggests; Cowork triggers and reports; people decide.
The Intake Coordinator's **Check inbox** can replace Cowork's scheduled start.

**Layers** (build status updated every phase)

1. Intake and storage (Python + API + CLI) - Built
2. AI review (Claude API + Python) - Not built
3. Policy lookup and PDFs (Python + API + React) - Built
4. Policy RAG (Python + Chroma) - Not built
5. Nurse decision (React + API) - Built (AI review panel waits on #2)
6. Systems of record (Python, mocked) - Built (drafted request waits on #2)
7. Cowork operator (Cowork + MCP) - Not built

**In the order it runs** (#n = layer above)

1. **#7** Cowork operator starts the run on a schedule - Not built
2. **#1** Intake and storage turns each new document into a case - Built
3. **#3** Policy lookup and PDFs picks the policy by CPT - Built
4. **#4** Policy RAG finds the criteria that matter - Not built
5. **#2** AI review reads, checks, cites and suggests - Not built
6. **#6** Systems of record sends the provider request if something is missing - Built (drafted request waits on #2)
7. **#7** Cowork operator reports what needs people - Not built
8. **#5** Nurse decision: Nurse approves or pends, Medical Director denies - Built (AI review panel waits on #2)
9. **#6** Systems of record syncs the decision and notifies the provider - Built
10. **#7** Cowork operator answers status questions (stuck cases, override rate) - Not built

## Setup
```bash
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then set DEMO_PASSWORD (e.g. demo) and DEMO_MODE=true
python -m app.cli init-db    # creates the DB + the 3 demo logins
cd ../frontend && npm install
```

## Run
```bash
# backend (from backend/, venv active)
uvicorn app.main:app --reload          # http://localhost:8000/docs
python -m app.cli status               # CLI
# frontend (from frontend/)
npm run dev                            # http://localhost:5173
```

## Demo run (CLI)
```bash
cd backend
python -m app.cli reset-demo --yes     # wipe + load the 3 sample faxes into inbox/
python -m app.cli poll                 # 3 new cases (Received)
python -m app.cli mark 1 ready         # test-only until Phase 3 AI review
python -m app.cli mark 2 incomplete --note "PT notes missing"
python -m app.cli mark 3 ready
python -m app.cli status
```
Then sign in on the web (see How to use) and decide cases 1 and 3.

## How to use

### Logins (seeded by `python -m app.cli init-db`)
All demo logins share one password: the value of **`DEMO_PASSWORD`** in `.env`.
With `DEMO_MODE=true` the login screen fills the password in for you. Click **?** on any screen for short steps, or open **💬 Guide Me** (bottom left) and tap **Guide me**: it reads who is signed in and where each case stands, then says the next step in plain words (including when to sign out and who to sign in as). Scripted, no AI; the AI chat will sit on the right in a later phase.
In demo mode, Received cases show a **Simulated AI check** (Check passed / Missing info) until Claude reviews cases in Phase 3.
**Presenter reset:** click the blank space just right of the "NurseOps Now" title in the header → confirm popup → all cases cleared and the 3 sample faxes back in the inbox (demo mode only).
_Before a public deploy, turn `DEMO_MODE` off (or accept that anyone with the URL can sign in)._

| Login | Name | Role |
|---|---|---|
| `nurse1` | Nora Diaz, RN | Nurse |
| `nurse2` | Sam Patel, RN | Nurse |
| `meddir` | Dr. Alex Kim, MD | Medical director |
| `intake1` | Riley Chen, Intake Coordinator | Intake coordinator |

### What each role can do
| Action | Nurse | Medical director | Intake coordinator |
|---|---|---|---|
| View queue, case detail, PDFs, audit log, metrics | yes | yes | yes |
| View / download medical policies (Policy tab on a case, policy row below the queue) | yes | yes | yes |
| Download a request PDF (logged in the audit log) | yes | yes | yes |
| Check inbox / upload a request | yes | yes | yes |
| Add documents to an Incomplete case | yes | yes | yes |
| Approve / Pend | yes | yes | **no (403)** |
| Deny (adverse determination) | **no (403)** | yes | **no (403)** |
| Ops CLI (`poll`, `mark`, `stuck`, `reset-demo`) | — | — | run from the terminal |

### Business rules you will hit
- **AI never decides.** Only a Nurse or Medical Director sets Approved / Pended, and **only the Medical Director can Deny** (as the policies say; enforced in `services/`, not the UI).
- **Rationale is required** for every decision.
- **Status order is enforced:** Received → Incomplete or ReadyForReview → Approved / Denied / Pended → Synced. A Received or Incomplete case can't be decided (409).
- **Pended** cases can be decided later (the review resumes automatically).
- **Approved / Denied** cases are pushed to the (mock) UM platform and the provider is notified → **Synced**.
- **Incomplete** cases send a provider request; when new documents arrive the case goes back to **Received**.
- **Override flag** is set when the decision disagrees with the AI tier (from Phase 3).
- Every change writes an **audit log** row (who, what, when); downloading a request PDF is logged too. All PDFs need a staff login.
- Until Phase 3, the test-only CLI `mark <id> ready|incomplete` stands in for the AI review.

### Handoff scripts
**W1: Complete request → decision** (samples A lumbar MRI and C brain MRI)

| Step | Who (role + seed login) | Does | Sees / expected |
|---|---|---|---|
| 1 | Intake coordinator `intake1` | Terminal: `reset-demo --yes`; web: **Check inbox** | 3 new cases, status Received |
| 2 | Ops (CLI) | `mark 1 ready` | Case 1 ReadyForReview |
| 3 | Nurse `nurse1` | Opens case 1, reads the PDF, **Approve** + rationale | Approved → Synced; "UM ref UM-000001; provider notified"; audit shows nurse1 |
| 4 | Medical director `meddir` | Queue, filter Synced | Case 1 with Nora Diaz, RN's decision; metrics 1 reviewed |

- Alternate (pend → escalate): `mark 3 ready` → `nurse1` **Pend** ("Needs MD review: headache, no red flags") → Pended → `meddir` **Deny** + rationale → Synced; audit shows nurse1 pended, meddir denied.
- Negative: `nurse1` tries to Deny case 3 → **403** ("Only a Medical Director can deny"); `intake1` opens case 3 → "Only nurses and medical directors can decide" (API → **403**); not logged in → **401**; deciding a Received case → **409**.

**W2: Incomplete request → provider sends documents → decision** (sample B, knee MRI)

| Step | Who (role + seed login) | Does | Sees / expected |
|---|---|---|---|
| 1 | Intake coordinator `intake1` | **Check inbox** | Case 2 Received |
| 2 | Ops (CLI) | `mark 2 incomplete --note "PT notes missing"` | Case 2 Incomplete; audit `provider_request_sent`; metrics rework 33% |
| 3 | Nurse `nurse1` | Opens case 2 | "No decision possible in status Incomplete" |
| 4 | Intake coordinator `intake1` | **Add documents** → `data/samples/followup/73721_b_followup_pt_notes.pdf` | Case 2 back to Received; viewer lists 2 documents |
| 5 | Ops (CLI) | `mark 2 ready` | Case 2 ReadyForReview |
| 6 | Nurse `nurse2` | **Approve** + "PT notes show 6 weeks, knee still catching" | Synced; audit shows Incomplete → Received → ReadyForReview → Approved → Synced |

- Alternate (provider doesn't respond): case 2 stays Incomplete; after 2 days it appears in `stuck --days 2`.
- Negative: deciding the Incomplete case → **409**; `intake1` deciding after step 5 → **403**.

_Full reference (terms like FAX / PRT / UPL, roles, rules, statuses, workflows, how Guide Me picks the next step): `backend/knowledge/guide_me.pdf`, generated by `python scripts/make_guide.py`. It is the source Guide Me will use for RAG + LLM later._

_Each script has a matching mocked test in `backend/tests/test_handoffs.py`. The AI-override script comes in Phase 3._

## Manual test
Backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`) running; open http://localhost:5173.
Start clean: `python -m app.cli init-db && python -m app.cli reset-demo --yes`.

- [ ] **Login per role:** sign in as `nurse1`, `nurse2`, `meddir`, `intake1` (password = `DEMO_PASSWORD`) → header shows the right name and role. Wrong password → "Wrong username or password".
- [ ] **Empty state:** before Check inbox → "No cases. Drop faxes in the inbox…".
- [ ] **Intake:** `intake1` → **Check inbox** → "3 new case(s)", all Received.
- [ ] **PDF viewer:** open any case → the request PDF shows with "SYNTHETIC — NOT REAL PHI".
- [ ] **Policy:** on a case, click the **Policy** tab → the matching policy (lumbar / knee / brain); **Download** saves the PDF. The **Medical policies** row below the queue shows all 3 with View (popup) and Download.
- [ ] **Wrong role:** `intake1` opens a ReadyForReview case → no decision form, "Only nurses and medical directors can decide".
- [ ] **W1 happy path:** steps above → case 1 Synced, metrics show 1 reviewed.
- [ ] **W1 alternate:** case 3 Pend by `nurse1`, Deny by `meddir` → audit shows both.
- [ ] **Rule: rationale required:** pick a decision with an empty rationale → button stays disabled.
- [ ] **W2 loop:** steps above → case 2 ends Synced with 2 documents.
- [ ] **Stuck:** `python -m app.cli stuck --days 0` → lists open cases (use `--days 2` in real use).
- [ ] **Filters:** queue Status / AI tier filters narrow the list; clicking a row opens the case; **Back to queue** works (no dead ends).
- [ ] **Seed twice:** `python -m app.cli init-db` twice → "0 reviewer(s) created" the second time (no duplicates).

## Test
```bash
cd backend && pytest                   # mocked, no API keys
cd frontend && npx vitest run
```

Synthetic data only. No real PHI.
