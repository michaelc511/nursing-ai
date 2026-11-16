# NurseOps Now: AI for Faster Prior Authorization

Intro from the plain-terms blog, then the core demo (yellow), then the close. Live site: https://nurseops-now.fly.dev

## Part 1: Intro

## #1 What the app is

When a doctor wants an expensive test for a patient, like an MRI, the health plan must say yes first. That's **prior authorization**. Today nurses at the plan read every request by hand (faxes, PDFs, uploads), check it against the plan's rules for that test, and decide. It's slow: 4.2 days on average, and 22% of requests come back because something was missing.

NurseOps Now is like giving that nurse team a very fast assistant that reads everything first and gets it ready, while the nurses still make the call. The goal is 40% faster (about 2.5 days) with no extra hires. That's a target; the prototype hasn't measured it on real work.

**Tech:** We used **FastAPI** (Python) to build one **service layer** that holds every rule, status change and log entry, **React + TypeScript (Vite)** for the web app, and **SQLite** through **SQLAlchemy** to store cases, decisions and the audit log, with the PDFs in a file folder (swappable later for Postgres and S3). We used **Docker** to package it and **Fly.io** to host it live, with the data on a persistent volume.

## #2 Opportunity 1: catch missing paperwork right away

**Today:** a request sits in a pile for days. When a nurse finally opens it, the physical therapy notes are missing, so she asks the doctor's office and waits again.

**With the app:** the moment the request arrives, it becomes a case and AI reads that case's PDF, says "this one is missing the PT notes", and drafts the note to the doctor's office. The wait starts on day 1, not day 3.

**Why it's good:** it goes straight at the 22% rework, the biggest source of delay.

**Cowork's part:** Cowork starts this. Its scheduled task calls `run_all`, which turns **each PDF in the inbox into its own case** and has Claude **read and check that case's PDF**, one case at a time, without anyone clicking. Cowork's report then lists each incomplete case and exactly what's missing (for example, "Case 5 is missing PT notes and the knee X-ray report"). A person can do the same with **Check inbox** in the web app.

**Tech:** We used the **Claude API** (Anthropic's LLM; Opus by default, Sonnet as fallback) to read the whole request PDF, sent as a native **document block** so Claude sees the text and the page images, and extract patient, CPT, ICD-10, provider and missing documents. We used **structured output** (`messages.parse`) with a **Pydantic** schema so Claude returns validated JSON, not free text. We used **pypdf** for page text and **RapidOCR** (local optical character recognition) for faxed or scanned pages, so no data leaves the server. We used a **regex** to read the CPT code in Python before calling the AI, so code picks the right policy. We used a mocked **notification service** to send the drafted provider request.

## #3 Opportunity 2: a study buddy for the nurse (copilot)

**Today:** the nurse reads a 10-page request and a 5-page policy and checks each rule herself.

**With the app:** AI has already done it: "Rule 1: met. Here's the exact sentence on page 2 that proves it." Then it suggests **likely approve**, **needs review** or **likely deny**. The app double-checks that every quoted sentence is really in the document, so the AI can't make things up.

**Why it's good:** the nurse goes from reading everything to checking the AI's work and deciding. She can still disagree, and the app records it when she does.

**Cowork's part:** the same `run_all` has Claude review every new case, and Cowork's report counts them by tier ("1 likely approve, 1 likely deny"). The full advice and the decision stay with the nurse in the web app; Cowork can't approve or deny.

**Tech:** We used **RAG** (retrieval-augmented generation) to find only the policy rules that matter: **sentence-transformers** embeddings in a **Chroma** vector database, **hybrid search** (BM25 keyword plus vector similarity), a **cross-encoder re-ranker** and **query rewriting**, over policies split into clause-sized chunks. We used **LangGraph** to run the review as fixed steps: read the CPT, look up the policy, retrieve the criteria, Claude reviews, code verifies. We used **Python quote verification** so any quote not found in the PDF forces "needs review". We used **versioned prompt files** so prompt changes are tracked like code, and the **service layer's state machine** so only people decide, with an **override flag** when a person disagrees with the AI.

## #4 Opportunity 3: always know where things stand

**Today:** doctors' offices call to ask "where's my request?", and managers can't easily see what's stuck.

**With the app:** anyone can ask. A manager types in Cowork "Which cases are stuck more than 2 days?" or "How often do nurses disagree with the AI?" and gets a plain-English answer. Nurses can ask AI Assist in the web app.

**Why it's good:** fewer phone calls, and leaders spot problems early.

**Cowork's part:** this is where Cowork matters most. It answers leaders' questions in plain English by calling read-only tools (`get_metrics`, `get_stuck_cases`, `get_cases`, `get_case`), from the same live data the nurses see.

**Tech:** We used **metrics services** (turnaround, rework rate, cases reviewed, override rate), shown as tiles in the web app and exposed as tools for Cowork. We used **AI Assist**, a **LangGraph agent** on Claude with **read-only tools** over the services plus **RAG** over the user guide, which remembers the conversation through **SqliteSaver** checkpoints.

## #5 Where Cowork fits

Think of Cowork as the **shift supervisor who never sleeps**. Every morning (or every 15 minutes in real life) it picks up the new requests, has the AI read and check each one, and reports: "3 new: 1 missing paperwork, 1 looks good, 1 doesn't meet the rules. Nothing decided, waiting on nurses."

**MCP** is the plug that connects Cowork to the app. It gives Cowork a fixed set of buttons: take in requests, check, report, answer questions. There's deliberately **no approve or deny button**, so Cowork can't make decisions.

**Scheduling it and what it costs.** The task runs on demand with **Run now**, and it can also run on a schedule: in the task's **Trigger**, choose **Schedule** and a frequency (the screenshot shows **Daily** at 09:29 AM). For the demo, daily or on demand is enough; in production you'd run it far more often (every 15 minutes, per `DEVPHASE3_COWORK.md`) or on an event such as a new fax arriving.

CostWhenAboutClaude API (the app's AI review)Only when there are new requests~$0.10 per new case; the 3 demo cases ~$0.30. An empty inbox costs $0 hereCowork (calling the tools, writing the report)Every runCounts toward your Claude plan's usage, not the app's API billFly.ioEvery run wakes the app if it's asleepPennies a day; it sleeps again after a few idle minutesSafety capsAlwaysThe app stops AI work at $0.50 per case and $10 per day (then people review); also set a spend limit in the Anthropic console

Example: a daily run with no new requests costs almost nothing; a day with 30 new requests costs about $3 in AI review. Check that scheduled tasks run while your computer is asleep or the Claude app is closed before relying on them; if not, keep the app open or use a server-side scheduler (cron) calling the same `run_all`.

**Tech:** We used **FastMCP** to build an **MCP server** (Model Context Protocol, the open standard for giving AI tools), mounted inside the same FastAPI app at `/mcp`, over **Streamable HTTP**, protected by a **bearer token**. It exposes **7 tools** (`run_all`, `poll_intake`, `review_case`, `get_cases`, `get_case`, `get_stuck_cases`, `get_metrics`) that call the same services as the web app, never the REST API, with **no decision tool**. We used **Claude Cowork** with a **custom connector** ("Prior Auth") and a **scheduled task** that calls `run_all`, then `get_metrics` and `get_stuck_cases`, and writes the report. Every MCP call goes to the **audit log** as "cowork", in the same database the web app reads.

## #6 Did we use agents?

Yes, two. The main AI review is deliberately not one.

PartAgent?How it works**Claude CoworkYes**Claude decides which MCP tools to call and in what order. It runs outside the app and can only use the 7 tools, with no decision tool**AI Assist** (chat in the web app)**Yes**A LangGraph graph: gate, agent, check, finish. In the agent step Claude chooses among 6 read-only tools (case lookup, case list, stuck cases, metrics, policy search, guide search) and calls as many as it needs. The gate blocks prompt injection and off-topic questions before Claude is called; the check step catches leaks and missing sources**AI review** (the nurse copilot)**No, a fixed workflow**Also LangGraph, but code sets the steps: read form, rewrite query, retrieve policy, Claude reviews, verify quotes, route. If verification fails it can retry; otherwise the case goes to a person

**Why the review isn't an agent:** it's the part that suggests approve or deny, so it must run the same way every time, in an order you can audit. Agents are used where flexibility helps: answering open questions (AI Assist) and operating the queue (Cowork). Multi-agent frameworks such as CrewAI and AutoGen weren't needed.

**Tech:** We used **LangGraph** for both the AI Assist agent (a tool-calling loop on Claude with read-only tools and SqliteSaver memory) and the fixed review workflow, and **Claude Cowork** as an external agent that operates the app through **MCP**. Neither agent has a tool that can approve or deny.

## #7 Keeping it safe and trustworthy

The app is built so the AI can't decide, can't be talked into misbehaving, and can always be checked.

**Cowork's part:** Cowork gets in only with a secret token, can only use the 7 tools (none of which can approve or deny), and every call it makes is in the audit log as "cowork".

**Tech:** We used **guardrails** (prompt-injection detection and intent gating) before the model is called, and **PII redaction** to strip SSNs, birth dates, phones, member IDs, NPIs, addresses and names from logs, chat memory and traces. We used **role-based login**, a **24-hour lockout** after 3 wrong passwords, **rate limits** and **cost caps** per case and per day. We used **LangSmith tracing** and token and cost accounting for every AI run, with a **semantic cache** to avoid paying twice. We used an **eval harness**: a golden set, an **LLM-as-judge**, **RAGAS** for faithfulness and relevance, a **red-team** suite (44 attacks, 0 got through), **pytest** (139 tests) and **vitest**, and a **CI eval gate** so quality can't silently drop.

## #8 The one rule

**AI reads and suggests. Cowork keeps the line moving. People decide.** A nurse can approve or put a case on hold; only the medical director can deny. Every step, by AI, Cowork or a person, is written down.

**Tech:** The rule is enforced once, in the **service layer**, so it holds for the web app, the CLI and MCP alike.

In one sentence: the AI does the reading and checking, Cowork keeps the line moving, and nurses spend their time on decisions instead of paperwork.

## Part 2: Core demo

## ★ Core demo: the most important part

This one loop covers the whole brief: the Cowork prototype, all 3 AI opportunities, and the rule that people decide. If time runs short, do only this.

**Before you start** (do these before the talk; one-time setup is already done):

- **Wake the app**: open https://nurseops-now.fly.dev (you'll wake it again in step 1, because it sleeps after a few idle minutes)

- **Fly CLI signed in**: `fly auth whoami` should print your account (it was on 2026-11-14). If not: `fly auth login`

- **Web app**: signed in as `nurse1`; a private window open on the login screen for `meddir`

- **Cowork**: the Claude app open, **Prior Auth** turned on, the **Prior auth intake** task saved

- **Optional, for a clean queue**: reset the demo (blank space right of the **NurseOps Now** title, **Yes, reset**, about $0.30). The queue then shows 3 cases, and the core demo adds 3 more

**1. New requests arrive.** In Terminal, first wake the app again (it sleeps after a few idle minutes, and `fly ssh` can't wake it). Wait for `200`:

curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" https://nurseops-now.fly.dev/api/health

Then right away, run this once. **What it does:** on the live server at Fly, it makes 3 new copies of the app's built-in sample request PDFs, from the sample folder `/app/data/samples/` into the inbox folder `/data/inbox/`. The originals stay where they are. The 3 copies are a lumbar spine MRI that's complete (arrives as a fax), a knee MRI missing its physical therapy notes (portal), and a brain MRI that doesn't meet the policy (upload). Landing in the inbox is how a real fax or upload would arrive. Running it twice adds 3 more.

fly ssh console --app nurseops-now -C "cp /app/data/samples/72148_a_complete.pdf /app/data/samples/73721_b_missing_pt.pdf /app/data/samples/70551_c_not_met.pdf /data/inbox/" Say: "I'm going to copy 3 sample prior-auth requests into the app's inbox, the way a fax or a portal upload would arrive: a lumbar spine MRI, a knee MRI and a brain MRI. Three new requests just arrived."

**2. Cowork runs the queue.** In Cowork: **Scheduled** > **Prior auth intake** > **Run now**, and click **Allow** for each tool (about 1.5 minutes). Each PDF becomes a case; Claude checks each one and suggests a tier. (No Cowork? Click **Check inbox** in the web app instead.)

Say: "Cowork connects through MCP and calls run all: it takes in each request, has Claude check it against the policy, and reports what needs people. It has no tool to approve or deny." (Opportunities 1 and 2)

**3. Show it in the web app.** Refresh the queue: the 3 new cases with their AI tiers. Open one and scroll to the audit log: it starts with **cowork**.

Say: "The cases are here with the AI's suggestion and citations, and the audit trail shows Cowork brought them in."

**4. The nurse decides** (`nurse1`). Open the likely-approve case: **Approve**, add a rationale, **Submit decision**. Open the likely-deny case: **Pend**, "Needs Medical Director review", **Submit decision**.

Say: "The AI suggested; the nurse decides. A nurse can't deny, and neither can the AI."

**5. The medical director decides** (`meddir`, private window). Open the pended case: **Deny**, add a rationale, **Submit decision**.

Say: "Only the medical director can deny. Every step, by Cowork, the AI and each person, is on the audit trail."

**6. Ask Cowork** (optional): "What's our override rate and turnaround time now?"

Say: "Leaders ask in plain English, from the same live data. Cowork is the operator, not the engine; people keep the decisions." (Opportunity 3)

## Part 3: Close

**Short:** "It's live on Fly.io with real Claude and synthetic data. AI does the reading and checking, Cowork runs the queue, and people keep the decisions."

"Extending it is cheap: a new policy is a PDF plus a re-index, and a new intake channel is one more door into the same services. On compliance, every AI output, decision, actor and timestamp is on the audit trail. This prototype uses synthetic data; real patient data needs HIPAA controls and a BAA first." "AI does the reading and the checking. Cowork runs the queue. People keep the decisions. That's how we get to 2.5 days without adding headcount. Thank you."

Likely questions:

- **Can the AI ever deny?** No. No tool, screen or service lets it. Only the medical director can deny.

- **How do you know the citations are right?** Code checks every quote against the PDF; a mismatch forces needs review.

- **What would production take?** HIPAA controls, a BAA, Postgres and cloud storage, and measuring turnaround on real cases.

After: switch off Mock or Debug mode if used, and reset the demo. More: after the talk · Q&A
