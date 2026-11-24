# War stories for an AI platform interview

:::html
<style>.tags{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:4px 0 10px;font-size:.88em}
.tags b{color:var(--muted);font-weight:600}.tags a{text-decoration:none;border:1px solid var(--accent);border-radius:14px;padding:2px 10px;
background:color-mix(in srgb,var(--accent) 10%,transparent);color:var(--fg)}.tags a:hover{background:color-mix(in srgb,var(--accent) 22%,transparent)}
.tags small{color:var(--muted)}.tags .flow{flex-basis:100%;color:var(--muted);font-size:.95em}</style>
<div class="tags"><b>Tags:</b>
<a href="#story-1-f0-the-real-problem-was-rework-not-the-decision">1 · Business → design <small>F0 · F21 · N6</small></a>
<a href="#story-2-f8-one-service-layer-three-clients">2 · Integrations <small>F4 · F8 · F12</small></a>
<a href="#story-3-f13-workflow-or-agent">3 · Agents <small>F13 · F16</small></a>
<a href="#story-4-f9-s5-the-trace-that-leaked-who-looked-at-which-case">4 · Privacy <small>F9 · S5</small></a>
<a href="#story-5-f6-n3-cost-as-a-design-input">5 · Cost <small>F6 · N3 · F2</small></a>
<a href="#story-6-f17-f20-the-eval-that-said-100">6 · Evals <small>F17 · F20</small></a>
<a href="#story-7-n4-real-mistakes-become-test-cases">7 · Quality loop <small>N4 · N5</small></a>
<a href="#story-8-f22-code-checks-every-quote">8 · Grounding <small>F3.1 · F22</small></a>
<a href="#story-9-f8-two-bugs-the-mocks-missed">9 · Reliability <small>F8 · F23</small></a>
<a href="#story-10-f24-n8-laptop-to-a-live-url">10 · Cloud <small>F24 · N8</small></a>
<a href="#story-11-f25-a-playbook-others-can-follow">11 · Leadership <small>F25</small></a>
<div class="flow">the problem → what I did → the measured result → the lesson → how it scales</div></div>
:::

Nov 23, 2026 · Michael Chang · Live demo: nurseops-now.fly.dev · Status: 11 stories (story 11 needs one work example from me)

**Read in this order**

1. [Why this post](#why-this-post) and [Words used in this post](#words-used-in-this-post): the goal and the terms
2. [Which story answers which topic](#which-story-answers-which-topic): pick a story by interview question
3. [Story 1 (F0): the real problem was rework, not the decision](#story-1-f0-the-real-problem-was-rework-not-the-decision)
4. [Story 2 (F8): one service layer, three clients](#story-2-f8-one-service-layer-three-clients)
5. [Story 3 (F13): workflow or agent](#story-3-f13-workflow-or-agent)
6. [Story 4 (F9, S5): the trace that leaked who looked at which case](#story-4-f9-s5-the-trace-that-leaked-who-looked-at-which-case)
7. [Story 5 (F6, N3): cost as a design input](#story-5-f6-n3-cost-as-a-design-input)
8. [Story 6 (F17, F20): the eval that said 100%](#story-6-f17-f20-the-eval-that-said-100)
9. [Story 7 (N4): real mistakes become test cases](#story-7-n4-real-mistakes-become-test-cases)
10. [Story 8 (F22): code checks every quote](#story-8-f22-code-checks-every-quote)
11. [Story 9 (F8): two bugs the mocks missed](#story-9-f8-two-bugs-the-mocks-missed)
12. [Story 10 (F24, N8): laptop to a live URL](#story-10-f24-n8-laptop-to-a-live-url)
13. [Story 11 (F25): a playbook others can follow](#story-11-f25-a-playbook-others-can-follow)
14. [The platform pitch](#the-platform-pitch) and [What this proves](#what-this-proves)

## Why this post

AI platform interviews ask about LLM integrations, agents, RAG, evals, security, cost and reliability, and about owning a problem from the business ask to a measured result. Each story here is a real problem from NurseOps Now, the prior-authorization copilot I scoped, built, tested and deployed, with the fix and the numbers. Every story names its feature numbers (F, S and N in super-features) and links to the pages that explain them.

Two earlier stories, chunking on headings and the eval that said 100%, are in [War stories](war-stories.html). This post adds the platform side: every story ends with **At platform scale**, how I'd run the same idea across many teams and apps. That's the difference between "an engineer who used AI tools" and someone who can lead an AI platform.

**Honest framing:** NurseOps Now is a working prototype with synthetic data, deployed on Fly.io. It hasn't had real users or production traffic. I say that once, plainly, and then talk about the decisions. An honest prototype with measured results beats a vague claim about scale.

**In plain terms:** a folder of "here's what broke, what I did and what it measured" stories, each with a line on how a whole company would do it.

## Words used in this post

| Term | Plain meaning | Everyday example |
|---|---|---|
| War story | A real problem, what was tried, and what fixed it | "The time the printer jammed before the board meeting" |
| Platform thinking | Building shared roads every team uses, not one-off apps | One company payroll system instead of each team paying people its own way |
| Service layer | The one place where all the business rules live | The bank's back office, whether you use the app, the ATM or the teller |
| Thin client | A screen or tool that only calls the service layer | An ATM: it can't decide your balance, it asks the bank |
| Override rate | How often people disagree with the AI's suggestion | How often a manager rewrites the intern's draft |
| Unverified-quote rate | How often the AI's quote can't be found in the source | Footnotes that point to pages that don't say that |
| Cost cap | A spending limit for AI calls | A prepaid card with a fixed amount |
| Graceful degradation | Keep working safely when part of the system fails | Stairs still work when the elevator breaks |
| LLM gateway | One shared front door for all AI model calls | A company travel desk that books every flight |
| Showback | Showing each team what it spent, without billing it | An itemized phone bill per family member |

## Which story answers which topic

| Interview topic | Stories |
|---|---|
| LLM integrations | [1](#story-1-f0-the-real-problem-was-rework-not-the-decision), [5](#story-5-f6-n3-cost-as-a-design-input), [9](#story-9-f8-two-bugs-the-mocks-missed) |
| Agentic workflows | [2](#story-2-f8-one-service-layer-three-clients), [3](#story-3-f13-workflow-or-agent), [9](#story-9-f8-two-bugs-the-mocks-missed) |
| RAG architectures | [6](#story-6-f17-f20-the-eval-that-said-100), [8](#story-8-f22-code-checks-every-quote), and story 1 in [War stories](war-stories.html) |
| Evaluation and observability | [6](#story-6-f17-f20-the-eval-that-said-100), [7](#story-7-n4-real-mistakes-become-test-cases), [4](#story-4-f9-s5-the-trace-that-leaked-who-looked-at-which-case) |
| Security and governance | [3](#story-3-f13-workflow-or-agent), [4](#story-4-f9-s5-the-trace-that-leaked-who-looked-at-which-case), [8](#story-8-f22-code-checks-every-quote) |
| Cost optimization | [5](#story-5-f6-n3-cost-as-a-design-input) |
| Reliability and performance | [5](#story-5-f6-n3-cost-as-a-design-input), [9](#story-9-f8-two-bugs-the-mocks-missed), [10](#story-10-f24-n8-laptop-to-a-live-url) |
| Business problem → technical solution | [1](#story-1-f0-the-real-problem-was-rework-not-the-decision) |
| Requirements and non-technical stakeholders | [1](#story-1-f0-the-real-problem-was-rework-not-the-decision), [3](#story-3-f13-workflow-or-agent), [9](#story-9-f8-two-bugs-the-mocks-missed) |
| Ownership: identified, proposed, led, measured | [4](#story-4-f9-s5-the-trace-that-leaked-who-looked-at-which-case), [6](#story-6-f17-f20-the-eval-that-said-100), [7](#story-7-n4-real-mistakes-become-test-cases), [10](#story-10-f24-n8-laptop-to-a-live-url) |
| Mentorship and technical leadership | [11](#story-11-f25-a-playbook-others-can-follow) |
| Cloud infrastructure | [10](#story-10-f24-n8-laptop-to-a-live-url) |
| Complex integrations | [2](#story-2-f8-one-service-layer-three-clients), [9](#story-9-f8-two-bugs-the-mocks-missed) |
| Idea to production | [1](#story-1-f0-the-real-problem-was-rework-not-the-decision), [10](#story-10-f24-n8-laptop-to-a-live-url) |

**In plain terms:** an index at the back of the book, sorted by the question the interviewer asks.

## Story 1 (F0): the real problem was rework, not the decision

**Features:** **F0 App Idea & Scope Design** (the main fix) · F13.1 State Machine · F21/S21 RBAC · N6 AI Governance
**Interview topics:** business → technical, stakeholders, idea to production

**Issue → solution:** "let AI approve the easy ones" was the wrong problem → aim the AI at the 22% rework, and make "AI never decides" a rule in code.

**The situation.** A regional health plan handles about 15,000 prior-authorization requests a month, with a 4.2-day average turnaround. Nurses review every request by hand. Documents arrive by fax, PDF, portal and upload, and providers call just to ask for a status.

**The problem.** The obvious pitch was "let AI approve the easy ones." That fails twice: a wrong denial harms a patient and creates regulatory risk, and clinical leadership would never adopt a tool that decides for them. When I mapped the work, the time wasn't in the decision. **22% of requests needed rework because information was missing**, and the trip back to the provider was what made cases slow.

**What I did:**

- I wrote a one-page scope with the goal in business terms: **4.2 days → about 2.5, with no added staff**. Success metrics cover turnaround, rework, cases reviewed and nurse agreement with the AI.
- I wrote the non-negotiables before any code: AI never approves or denies, every AI claim cites a page and a quote, and every decision is audited.
- I aimed the AI at the bottleneck. It extracts the request, flags missing documents up front and drafts the request to the provider. Then it gives the nurse a cited summary with a suggested tier.
- I turned "AI never decides" into code. A state machine in the service layer allows only listed status moves. Nurses can approve or pend, and only a medical director can deny. A request that skips the UI still gets rejected.

**The result.** The speedup comes from preparing the case, not from removing the nurse, and that makes the tool adoptable. Tests prove the rule: two non-human attempts to approve were refused, the human approval worked, and both real moves were audited. The **override rate** gives clinical leadership a metric for when to trust the AI more.

**The lesson:** find where the time actually goes before choosing what the AI does. The stakeholder's real constraint ("we can't let a machine deny care") becomes a design rule, not an objection to manage.

**Short version for an interview (about 30 seconds):**
"The ask sounded like 'automate prior auth.' When I mapped the work, the delay was 22% rework from missing information, not the decision. So I scoped the AI to prepare the case: extract details, flag missing documents up front, and give the nurse a cited summary. I made 'AI never decides' a state machine in the service layer, so only a nurse can approve and only a medical director can deny. The target is 4.2 days down to about 2.5 with no added staff, and nurse override rate is the trust metric leadership watches."

**At platform scale:** every AI use case gets the same intake template: the business metric, the human decision owner, the non-negotiables and the eval set. Teams fill it in before they get API keys.

**In plain terms:** don't hire a robot to sign the checks. Hire it to make sure every form is complete before it reaches the person who signs.

**Read more:** [Feature blog, F0](nurseops-now-blog.html#p-f0) · [State blog, Step 7: case state machine](nurseops-now-state-bk7.html#step-7-case-state-machine) · [Feature blog, F21/S21](nurseops-now-blog.html#p-f21-s21)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 2 (F8): one service layer, three clients

**Features:** **F8 FastMCP Server** (the main fix) · F4/S16 FastAPI Backend · F12 Engine Strategy Factory · F13.2 Agentic RAG
**Interview topics:** complex integrations, platform architecture, agentic workflows

**Issue → solution:** an AI client wired to the REST API would re-implement the rules and find a way around them → one thick service layer, thin clients, and agent tools that simply don't include decisions.

**The situation.** NurseOps Now needed three ways in: a React web app for nurses, a Typer CLI for operations, and an MCP server so Claude Cowork could run intake on a schedule.

**The problem.** The fast way to add an AI client is to point it at the REST API, or give it its own database access. Then every client re-implements the business rules, and the AI client is the one most likely to find a path around them.

**What I did:**

- I put all the business rules in **one thick service layer**. The web app, the CLI and the MCP server are thin clients over the same functions.
- The FastMCP server calls the service layer directly, never REST. It exposes seven tools (`run_all`, `poll_intake`, `review_case`, `get_cases`, `get_case`, `get_stuck_cases`, `get_metrics`) over Streamable HTTP with a bearer token. Every call runs as the actor `cowork`, so the audit log shows what the agent did.
- **No MCP tool can approve, pend or deny.** That isn't a prompt instruction. Those functions aren't exposed, and the state machine would refuse them anyway.
- I connected Claude Cowork to the deployed app as a custom connector, with a scheduled "Prior auth intake" task.

**The result.** On Nov 14, 2026, Cowork listed all 7 tools and answered a live operations question with real data (3 cases stuck 4 days, 33% rework). It then ran intake on three sample PDFs for about $0.30, creating and reviewing three cases: one likely approve, one likely deny and one incomplete. The agent client added no new rules to keep in sync.

**The lesson:** give agents the same front door as people, with fewer keys. Least privilege for an agent means the dangerous tool doesn't exist, not that the prompt says "please don't."

**Short version for an interview (about 30 seconds):**
"I built one service layer with three thin clients: the web app, a CLI and an MCP server for Claude Cowork. The MCP tools call the service layer directly, every call is audited as the 'cowork' actor, and there's no tool that can approve or deny. So the agent gets the same rules as a person, with fewer permissions. Cowork ran scheduled intake on three cases for about thirty cents."

**At platform scale:** every internal system exposes an MCP server over its service layer, behind a shared gateway for identity, scopes and audit. Agent capabilities become an access-control decision, not a code change.

**In plain terms:** the new assistant gets a badge for the same building as everyone else, but the badge doesn't open the vault.

**Read more:** [Feature blog, F8](nurseops-now-blog.html#p-f8) · [Feature blog, F12](nurseops-now-blog.html#p-f12) · [Feature blog, F13.2](nurseops-now-blog.html#p-f13-2)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 3 (F13): workflow or agent

**Features:** **F13/S17 LangGraph Engines** (the main fix) · F13.1 State Machine · F13.2 Agentic RAG · F16 Checkpointing
**Interview topics:** agentic workflows, architecture, governance

**Issue → solution:** a free-running agent can't be audited on a clinical path, but hard-coding every staff question is endless → a fixed workflow for decisions and an agent for questions, drawn by the cost of a wrong step.

**The situation.** There were two kinds of AI work: reviewing a clinical case against policy, and answering staff questions like "which cases are stuck?" or "what does the knee MRI policy require?"

**The problem.** A free-running agent is flexible but hard to test, predict or audit. On a clinical decision path, an unpredictable step is a compliance problem.

**What I did:**

- **Case review is a fixed LangGraph workflow:** `read_form → rewrite_query → retrieve_policy → ai_review → verify → route`. Only the review and rewrite steps call the model. The `verify` node checks every quote, the CPT code and injection flags, and sends failures back to `ai_review` **once**. There's a step cap and a per-case cost cap ($0.50 by default), and each node's timing is saved with the review.
- **Staff Q&A is an agent** (AI Assist) that chooses among six **read-only** tools (`get_case`, `list_cases`, `stuck_cases`, `metrics`, `search_policy`, `search_guide`), capped at 4 tool rounds. Its memory is checkpointed per user and case thread, so it survives restarts.
- I kept a **frozen linear baseline** of the review. Tests check that the graph and the baseline give the same tier and status on the demo cases.

**The result.** The critical path is predictable and every step is visible. The flexible part is where a wrong step costs a re-ask, not a wrong denial. The eval found the agent's weak spot honestly: the judge scored AI Assist faithfulness 3/5 on one case, because it sometimes cited details its tools hadn't returned. That's the expected failure mode of agents, and why it isn't on the decision path.

**The lesson:** pick workflow vs. agent by the cost of a wrong step, not by fashion. Fixed graphs for decisions, agents for exploration, and always cap steps, cost and permissions.

**Short version for an interview (about 30 seconds):**
"I split it by risk. The clinical review is a fixed LangGraph state machine: read, rewrite, retrieve, review, verify, route, with one retry, a step cap and a fifty-cent cost cap per case. Staff questions go to an agent with six read-only tools and four tool rounds max. The eval showed the agent sometimes cites things its tools didn't return, which is exactly why it isn't on the decision path."

**At platform scale:** the platform offers both patterns as templates with caps, tracing and eval hooks built in, plus a review checklist for moving a use case between them.

**In plain terms:** a pilot follows the checklist for takeoff but talks freely with the tower. Use the checklist where a mistake is expensive.

**Read more:** [Feature blog, F13.1](nurseops-now-blog.html#p-f13-1) · [Feature blog, F13.2](nurseops-now-blog.html#p-f13-2) · [State blog, Step 3](nurseops-now-state-bk7.html#step-3-load-facts-only-when-needed)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 4 (F9, S5): the trace that leaked who looked at which case

**Features:** **F9/S15 Tracing** and **S5 PII Sanitization** (the main fix) · F16 Checkpointing · N6 Governance
**Interview topics:** security and governance, observability, ownership

**Issue → solution:** the `user:case` thread ID was reaching the tracing vendor in metadata → hash it, and redact before anything is saved or traced.

**The situation.** On Nov 11, 2026 I added LangSmith tracing to three deployed AI apps: run names, tags, model, prompt version, tokens and cost on every LLM call, and spans for retrieval and tool steps.

**The problem.** NurseOps Now handles (synthetic) patient data, so traces must carry no content. LangSmith inputs and outputs are hidden unless a flag turns them on. But the AI Assist **thread ID was `user:case`**, and it flowed into LangSmith **metadata**. Metadata isn't "content," so content-hiding didn't cover it. Who looked at which case was going to a third party.

**What I did:**

- **Identified:** a privacy test that checks what reaches the tracing layer caught it before release.
- **Fixed:** the thread ID is now **hashed** before it reaches LangSmith metadata. It still groups runs, but it can't be read.
- **Hardened the rest:** `pii.py` redacts SSNs, dates, phones, emails, member IDs, NPIs, addresses and the names extracted for that case. It runs on logs, AI Assist memory and feedback text before anything is saved. The local `traces` table stores timings, tokens, cost and outcome, never content.

**The result.** Shipped with 137 tests passing and deployed the same day (Fly release v6). Saved memory keeps no personal details: date of birth, phone and SSN were confirmed masked in the demo.

**The lesson:** personal data hides in identifiers and metadata, not just prompt text. Observability is a data flow to a vendor and needs the same privacy review as any integration.

**Short version for an interview (about 30 seconds):**
"When I added LangSmith tracing, content was hidden by default, but our privacy test caught the thread ID, user plus case, flowing into trace metadata. That's who looked at which patient going to a vendor. I hashed it, kept it useful for grouping, and made sure redaction runs before anything is saved or traced. Identifiers leak too, not just prompts."

**At platform scale:** tracing goes through one shared wrapper that redacts and hashes centrally, plus a CI privacy test that fails if raw identifiers reach any exporter. Teams can't opt out by accident.

**In plain terms:** you blacked out the names in the letter but left them on the envelope.

**Read more:** [Feature blog, F9](nurseops-now-blog.html#p-f9) · [Feature blog, S5](nurseops-now-blog.html#p-s5) · [State blog, Step 6: mask, then save](nurseops-now-state-bk7.html#step-6-mask-then-save-the-turn)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 5 (F6, N3): cost as a design input

**Features:** **F6/S15 Token & Cost Accounting** and **N3 Caching & Fallback** (the main fix) · F2/S6 LLM Selector · F21/S21 Rate Limiting
**Interview topics:** cost optimization, reliability, LLM integrations

**Issue → solution:** a public app on a paid model could run up an unbounded bill, and model choices were guesses → measure every call, avoid calls, cap the rest, and fail toward a person.

**The situation.** NurseOps Now runs on Claude, with Opus 5.5 by default, and it's publicly reachable as a demo. Every review, agent turn and scheduled run spends real money.

**What I did**, cheapest layer first:

- **Measure:** every call goes to `llm_calls` with tokens, cost and latency (never prompts). `pricing.py` converts tokens to dollars, and `/api/ai/usage` reports totals and per-case cost.
- **Don't call:** intent gating is a keyword check with **no AI call**, so off-topic questions cost nothing. Exact repeats come from a response cache, and the unchanged system prompt is prompt-cached on reviews.
- **Cap:** $0.50 per case, 20 AI calls per user per minute and $10 per day. Going over returns a 429 and writes an audit entry.
- **Choose:** models are configuration (Opus, Sonnet or Haiku 5.5), switchable without a code change.
- **Degrade safely:** if the main model is overloaded, it falls back to Sonnet. If every model fails, the case goes to a person with an "AI unavailable" warning. Production never shows mock answers.

**The result.** I know what things cost: a live case review was about $0.11 (Nov 10, 2026), a scheduled 3-case intake about $0.30 (Nov 14), and a full live eval run $0.42 (Nov 19). Those numbers drive decisions, like running the live eval before a release rather than on every commit.

**The lesson:** cost per answer is a product metric. Measure every call, skip the calls you don't need, cap the rest, and fail closed toward a human.

**Short version for an interview (about 30 seconds):**
"I treat cost as a design input. Every call logs tokens, cost and latency. Off-topic questions are blocked by a no-AI keyword gate, repeats come from cache, and the system prompt is prompt-cached. There are hard caps per case, per user per minute and per day. A review costs about eleven cents, so I can reason about 15,000 cases a month. If the model's down, it falls back to Sonnet, and if everything's down, the case goes to a person."

**At platform scale:** an LLM gateway owns pricing, per-team budgets, caching, routing and failover. Showback dashboards give each team its cost per answer, so model choices are made with data.

**Honest gap:** routing is manual today. There's no automatic easy-to-Haiku, hard-to-Opus routing yet, and the cache matches exact inputs, not meaning. Those are the next two steps.

**In plain terms:** check the price tag, don't buy what you don't need, set a budget, and have a plan B when the store is closed.

**Read more:** [Feature blog, F6](nurseops-now-blog.html#p-f6) · [Feature blog, N3](nurseops-now-blog.html#p-n3) · [State blog, Step 8: caching](nurseops-now-state-bk7.html#step-8-reuse-instead-of-recompute)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 6 (F17, F20): the eval that said 100%

**Features:** **F17 RAG Evals Harness** and **F20 CI/CD Eval Regression Gate**
**Interview topics:** evaluation, ownership

Told in full in [War stories, story 2](war-stories.html#war-story-2-f17-f20-the-eval-said-100-fixed-by-making-the-test-as-hard-as-real-life). The ownership angle: every retrieval method scored 100% on the golden set. Instead of celebrating, I treated it as a broken test. I expanded the policies from 1 page to 5 (21 → 83 chunks). Offline hit@1 dropped from 0.889 to 0.778 and live faithfulness from 0.893 to 0.775. The CI gate failed on its own (`GATE FAILED: hit@1 0.889 -> 0.778`), and the harder test exposed real misses I could then fix.

**In plain terms:** a test everyone passes isn't a test.

[↑ Back to the list](#which-story-answers-which-topic)

## Story 7 (N4): real mistakes become test cases

**Features:** **N4 Online Quality Monitoring** (the main fix) · F17 Evals · F20 CI Gate · N5 Red Teaming
**Interview topics:** evaluation and observability, ownership (measure results)

**Issue → solution:** an offline eval only tests the questions I thought of → watch live signals, and turn real failures into golden cases the gate guards.

**The situation.** An offline eval tells you it worked before launch. It doesn't tell you it still works next month.

**The problem.** With a golden set of 20 cases, quality is judged on my questions. Real failures look different, and nobody would notice drift until a nurse complained.

**What I did:**

- **Online signals:** `/api/ai/quality` reports thumbs up and down, the **override rate**, the **unverified-quote rate**, AI-unavailable reviews, cost and latency, with alerts for drift.
- **Feedback loop:** the CLI command `export-feedback` writes thumbs-down items to `evaluation/candidates.jsonl`. A person reviews them and promotes the good ones into the golden set, so the CI gate guards that exact failure from then on.
- **Gate rules:** the gate fails on **any** safety failure, or any score more than 0.05 below the baseline.
- **Attacks:** a red-team suite generates 44 attacks (injection variants, prompt extraction, fake authority, decision requests, off-topic). An attack counts as handled only if it causes no decision, no leak and no status change. All 44 were handled, offline and on real Claude.

**The result.** The live baseline (Nov 10, 2026, original policies) was retrieval 1.0, review 1.0, AI Assist 0.875, safety 1.0 and faithfulness 0.893. Quality has a number before release, a gate at merge, and a signal in production that feeds back into the gate.

**The lesson:** grow the eval set from production, not from imagination. In a human-in-the-loop system, override rate is the best single metric, because the expert grades the AI for free.

**Short version for an interview (about 30 seconds):**
"I built quality as a loop. Offline, there's a golden set with an LLM judge and RAGAS, and a CI gate that fails on any safety miss or a drop of more than 0.05. In production, I track thumbs, nurse override rate and unverified-quote rate. Thumbs-down items export to a candidates file, a person promotes them to the golden set, and the gate then protects against that failure forever. Red team: 44 attacks, 44 handled."

**At platform scale:** a shared eval service holds every app's golden sets, judges and baselines, a shared feedback widget and override logging feed it, and every app gets the same release gate.

**Honest gap:** the live gate in GitHub Actions needs the API key as a repository secret, which isn't added yet, so CI runs the offline gate. The eval plan's next steps: grow the golden set from 20 to about 60 hard cases, grade the grader, and measure run-to-run noise.

**In plain terms:** every customer complaint becomes a new question on the next practice exam.

**Read more:** [Feature blog, N4](nurseops-now-blog.html#p-n4) · [Feature blog, N5](nurseops-now-blog.html#p-n5) · [Eval plan, Step 12: after release](nurseops-now-evals.html#step-12-after-release) · [Eval plan, Step 11: CI gate](nurseops-now-evals.html#step-11-ci-gate)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 8 (F22): code checks every quote

**Features:** **F13.1 Verify-and-Retry** and **F22 Prompt-Injection Defense** (the main fix) · F3.1/S11,S12 Prompt & Grounding
**Interview topics:** reliability, security, RAG

**Issue → solution:** "a schema stops hallucination" is wrong, since a well-formed answer can hold a made-up quote → check every quote in code, and fail toward a person.

**The situation.** Each review returns JSON validated by Pydantic: extracted fields, missing items, criteria met or not, a tier, and a page and quote for every claim.

**The problem.** A schema stops malformed answers, but a perfectly formed answer can still contain a made-up quote. In a clinical review, a fabricated citation is worse than none, because it looks trustworthy.

**What I did:**

- **Verify in code, not in the model:** the `verify` node checks every quote against the source PDF. A mismatch gets **one** retry. If it still fails, the case goes to **needs review** and counts in the unverified-quote rate.
- **Treat documents as data:** clinical text is fenced in `<document>` tags, and the prompt says document text is data. An injection match doesn't silently drop the case. It forces needs review and shows the nurse a flag. Output guardrails block any answer that leaks the system prompt or a key.

**The result.** The first live Claude review (Nov 10, 2026) came back likely approve with **all quotes verified**, for about $0.11. Injected text can't produce a decision: the worst case is a flagged case in a human queue.

**The lesson:** turn "trust the model" into "verify the model." Anything code can check, code should check, and anything uncertain fails toward a person.

**Short version for an interview (about 30 seconds):**
"Pydantic guarantees the shape, not the truth. So every quote the AI cites is checked in code against the source PDF. A miss gets one retry, then the case goes to a nurse and counts toward the unverified-quote rate. Injected text in a document gets flagged and routed to a person too. The worst case is always a human looking at it, never a wrong decision."

**At platform scale:** citation checking and document fencing are shared library functions every RAG app uses, and unverified-quote rate is a standard dashboard metric.

**In plain terms:** don't just check the footnote is formatted right. Open the book and make sure the page says it.

**Read more:** [Feature blog, F22](nurseops-now-blog.html#p-f22) · [State blog, Step 11: ground every answer](nurseops-now-state-bk7.html#step-11-ground-every-answer) · [Eval plan, Step 8: output checks](nurseops-now-evals.html#step-8-output-checks)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 9 (F8): two bugs the mocks missed

**Features:** **F23 Unit Tests** and **F8 FastMCP Server** · N1 Document Parsing
**Interview topics:** reliability, complex integrations, stakeholders (who sees the failure)

**Issue → solution:** all mocked tests were green, but real clients broke → run the real flows on an isolated copy before deploy, and fix the contract.

**The situation.** On Nov 10, 2026, before deploying, 120 backend tests and 19 frontend tests were passing, all fully mocked. Then I ran the API flows on an isolated copy and connected real clients.

**The problem.** Two real failures got past the green tests:

1. `POST /mcp` without a trailing slash returned **405**, but the docs and client setup said `/mcp`. Every MCP client set up from our own docs would have failed to connect.
2. A garbage non-PDF upload through the web app could reach **ReadyForReview**, putting junk in a nurse's queue as if it were a real case.

**What I did.** I fixed both: `/mcp` now works with or without the slash, and web uploads reject fake files. One thing I deliberately didn't change: files in the intake inbox still go to a human, because an operator should see an odd fax, not have it silently dropped.

**The result.** Tests grew to 128, and later to 139 backend plus 22 frontend. The deployed app passed live checks on real Claude: health, UI, login, injection blocked, MCP token and real reviews.

**The lesson:** mocked tests prove the logic, and integration checks against real clients prove the contract. Also think about who sees a failure: a junk case costs a nurse's time and trust.

**Short version for an interview (about 30 seconds):**
"All our mocked tests were green, then real integration found two bugs. The MCP endpoint returned 405 without a trailing slash, so anyone following our docs couldn't connect, and fake uploads could land in a nurse's review queue. I fixed both, but kept odd inbox files routed to a human on purpose. Mocks prove the logic; real clients prove the contract."

**At platform scale:** every service ships contract tests that run its documented client setup, and a pre-deploy smoke test with real clients, not just mocks.

**In plain terms:** the car passed every test on the bench, then the key didn't fit the door.

**Read more:** [Feature blog, F8](nurseops-now-blog.html#p-f8) · [Eval plan, Step 2: read the request](nurseops-now-evals.html#step-2-read-the-request)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 10 (F24, N8): laptop to a live URL

**Features:** **F24 Deploy** and **N8 Production Ops & Compliance** · F21/S21 Auth & Rate Limiting
**Interview topics:** cloud infrastructure, idea to production, ownership

**Issue → solution:** a public URL running real Claude calls on a paid key → container, host secrets, a local load test first, then lockout and caps on the public surface.

**The situation.** A public demo URL for reviewers and stakeholders, running real Claude calls on my API key.

**What I did:**

- **Container:** a single Docker image (about 545 MB) serving the React app and FastAPI. A persistent volume holds the database and files, and secrets live on the host, never in the repo.
- **Tested the real container locally first:** all flows passed, and a load test ran with 0 errors.
- **Deployed to Fly.io** on Nov 10, 2026 and ran live checks on real Claude.
- **Hardened the public surface after launch:** 3 wrong passwords lock that address for 24 hours, with a CLI unlock command. The demo password is only filled in with `?demo=y`, masked and never shown as text. Rate and cost caps ([story 5](#story-5-f6-n3-cost-as-a-design-input)) bound the spend.
- **Ops plan (N8):** SSO, SLOs and alerts, backups and disaster recovery, data retention and a governance doc. Real patient data would also need BAAs with vendors.

**The result.** Live at nurseops-now.fly.dev through 9 releases. Every change goes through tests, ship, deploy and a live check.

**The lesson:** the AI is maybe half of an enterprise system. The other half is the production basics, and I own both.

**Short version for an interview (about 30 seconds):**
"I took it from laptop to a live URL: one Docker image, a persistent volume, secrets on the host, a local load test with zero errors, then Fly.io. After launch I hardened the public surface with a login lockout, a masked demo password and per-user and daily cost caps. It's been through nine releases, each one tests, ship, deploy, live check."

**Honest gap (say it before they ask):** this is Fly.io, not AWS, at demo scale. The concepts map directly: container to ECS or EKS, volume to EBS or RDS, host secrets to Secrets Manager, traces to Datadog or CloudWatch. I'd be ramping on the AWS specifics, not the ideas.

**At platform scale:** a golden-path deploy template (container, secrets manager, SLOs, alerts, runbooks) that every AI app starts from, so each team doesn't rebuild production basics.

**In plain terms:** the recipe is half the restaurant. The other half is the kitchen, the locks and the fire exits.

**Read more:** [Feature blog, F24](nurseops-now-blog.html#p-f24) · [Feature blog, N8](nurseops-now-blog.html#p-n8)

[↑ Back to the list](#which-story-answers-which-topic)

## Story 11 (F25): a playbook others can follow

**Features:** **F25 Retro & Memory** (the main fix) · N6 AI Governance
**Interview topics:** technical leadership, mentorship, platform thinking

**Issue → solution:** every AI app re-decided the same things, and the lessons lived in my head → a written playbook, a 42-feature catalog with tiers, and retros that feed it.

**The situation.** I built several AI apps in a row: a restaurant RAG assistant, a plant operations manager and NurseOps Now.

**The problem.** Each one re-decided chunking, evals, guardrails and deploy from scratch.

**What I did:**

- I wrote a **12-phase build playbook** with a catalog of **42 features** (super-features), each with a tier (Required, Recommended for…, Optional), so a team picks consciously instead of reinventing.
- Every phase records its decisions and timing. Retros feed lessons back into the playbook, so the next project starts from the last one's lessons.
- I wrote the decisions up for others: feature blogs, an eval plan, a state-management write-up, deep dives and these war stories, each with the trade-off and the evidence.

**The result.** NurseOps Now built 37 of the 42 features. It skipped 4 on purpose, with a written reason for each (text-to-SQL, CrewAI, AutoGen and GraphRAG didn't fit), instead of skipping them by accident.

**The lesson:** a platform is mostly paved roads: defaults, templates and checklists that make the right choice the easy one.

**To add before using:** one real work example of mentoring or leading engineers (ServiceNow, Sleep Number or Oracle). This story shows leadership by enablement, but the interviewer will want a person I helped grow.

**In plain terms:** write the recipe down so the next cook doesn't have to call you.

**Read more:** [Feature blog, F25](nurseops-now-blog.html#p-f25) · [Feature blog, all 42 features](nurseops-now-blog.html)

[↑ Back to the list](#which-story-answers-which-topic)

## The platform pitch

To open or close (about 60 seconds):

"I think about AI as a platform, not a feature. In NurseOps Now I started from the business metric, 4.2 days to 2.5 by attacking 22% rework, and made the stakeholder's constraint, AI never decides, a rule in the service layer. On top of that is one service layer with thin clients, including an MCP server so agents get the same front door as people with fewer keys. Workflows handle decisions and agents handle exploration, both capped on steps, cost and permissions. Quality is a loop: golden set, LLM judge, a CI gate, red team, and production signals like override rate feeding back into the tests. Cost and privacy are built into a shared tracing and gateway layer. At company scale, those same pieces become the paved road every team ships on."

**In plain terms:** one minute that says "I don't just build the app, I build the road the apps drive on."

## What this proves

Each story starts from a real problem in NurseOps Now and ends with a measured result and how the same fix scales across a company: scoping to the business metric, one service layer for people and agents, workflows vs. agents by risk, privacy in observability, cost as a design input, an honest eval loop, verified citations, real-client testing and a live deploy. The gaps (no real users, Fly.io not AWS, manual model routing, the live CI gate) are named, not hidden.

All NurseOps Now policies and cases are synthetic. No real patient data is used.
