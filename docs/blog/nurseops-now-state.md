# Remembering the right things: state management in NurseOps Now

:::html
<style>.tags{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:4px 0 10px;font-size:.88em}
.tags b{color:var(--muted);font-weight:600}.tags a{text-decoration:none;border:1px solid var(--accent);border-radius:14px;padding:2px 10px;
background:color-mix(in srgb,var(--accent) 10%,transparent);color:var(--fg)}.tags a:hover{background:color-mix(in srgb,var(--accent) 22%,transparent)}
.tags small{color:var(--muted)}.tags .flow{flex-basis:100%;color:var(--muted);font-size:.95em}
td>b,.bk{background:#ffe866;color:#1c1f23;border-radius:4px;padding:1px 4px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
td>b a.term,td>b a.term:hover{background:transparent;color:#1c1f23;border-bottom-color:#8a6d00}td>b .def{color:#4a4000}
span[id^="outcome-"]~b:nth-of-type(2){background:#ffe866;color:#1c1f23;border-radius:4px;padding:1px 4px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
span[id^="outcome-"]~b:nth-of-type(2) a.term,span[id^="outcome-"]~b:nth-of-type(2) a.term:hover{background:transparent;color:#1c1f23;border-bottom-color:#8a6d00}span[id^="outcome-"]~b:nth-of-type(2) .def{color:#4a4000}</style>
<div class="tags"><b>Tags:</b>
<a href="#context-and-state-management-intro">Intro <small>the problem</small></a>
<a href="#implementing-short-term-memory-token-budgets-and-window-management-7-1">Short-term memory <small>(7.1)</small></a>
<a href="#compression-strategies-summarization-and-entity-extraction-7-2">Compression <small>(7.2)</small></a>
<a href="#implementing-long-term-memory-external-persistence-architecture-7-3">Long-term memory <small>(7.3)</small></a>
<a href="#preventing-drift-and-hallucinations-in-long-running-agents-7-4">Drift and hallucinations <small>(7.4)</small></a>
<div class="flow">the problem → fit the window → keep facts exact → save it → keep it on task and truthful</div></div>
:::

Nov 19, 2026 (updated Nov 20) · Michael Chang · Live demo: nurseops-now.fly.dev · Status: built; 6 gaps named, plan below

**Read in this order**

1. [Why this post](#why-this-post): where the ideas come from, and how this differs from the RAG and eval posts
2. [Words used in this post](#words-used-in-this-post): the terms
3. [How a chat turn flows, and where state lives](#how-a-chat-turn-flows-and-where-state-lives): the 4 Agentic Outcomes (problem → goal → what we built), then every solution from the book first (bold), then ours, on one page
4. [Context and State Management (Intro)](#context-and-state-management-intro): the problem, and the plan in one page
5. [Implementing Short-Term Memory: Token Budgets and Window Management (7.1)](#implementing-short-term-memory-token-budgets-and-window-management-7-1)
6. [Compression Strategies: Summarization and Entity Extraction (7.2)](#compression-strategies-summarization-and-entity-extraction-7-2)
7. [Implementing Long-Term Memory: External Persistence Architecture (7.3)](#implementing-long-term-memory-external-persistence-architecture-7-3)
8. [Preventing Drift and Hallucinations in Long-Running Agents (7.4)](#preventing-drift-and-hallucinations-in-long-running-agents-7-4)
9. [The chapter vs. NurseOps Now](#the-chapter-vs-nurseops-now), [Checklist](#checklist-what-is-done-and-what-is-next), [Findings](#findings-what-the-demos-showed), [Plan](#plan-closing-the-gaps), [Tools](#tools) and [What this proves](#what-this-proves)

## Why this post

**Where the idea comes from.** This post follows Chapter 7, _Context and State Management_, of an AI engineering book I'm studying. The chapter has an intro and four parts: managing the window (7.1), compressing history (7.2), saving state outside the model (7.3), and keeping a long-running agent on task and truthful (7.4). This post follows the same order, using the chapter's own section titles. For each part it states **the problem** and **how NurseOps Now solves it**, with the real code and output, what isn't built yet, and where I'd correct the chapter. Every problem and solution is also tagged with the memory type it deals with: working, episodic, semantic or procedural ([the four memory types](#context-and-state-management-intro)).

**How this differs from the other posts.** The [ingestion deep dive](deep-dives/01-ingestion.html) is about finding the right policy text (RAG). The [eval plan](nurseops-now-evals.html) is about proving answers are good. This post is about **memory**: what the AI is given on each call, what is saved, for whom, for how long, and what must never be summarized or leaked. Each step has the two usual halves: the **strategy** (what we built) and the **proof** (how it's checked).

**In plain terms:** the chapter is a checklist for an AI's memory; this post holds it up against a real app, item by item.

## Words used in this post

| Term | Plain meaning | Everyday example |
|---|---|---|
| State | Everything the app must remember to continue correctly | Where you left off in a book |
| Context window | Everything sent to the AI in one call; it has a size limit | The desk space you can work on at once |
| Token | The unit the AI reads and is billed by; roughly ¾ of a word | Paying per word |
| Thread | One saved conversation, here one per user and case | One email thread |
| Checkpoint | A saved copy of a conversation's state after each step | A game's save point |
| Hot state | What's in the current call | What's on your desk now |
| Cold state | What's saved in a database for later | The filing cabinet |
| Rehydration | Loading saved state back in for a new call | Opening the file before a meeting |
| State machine | A fixed list of allowed status changes | A form that can only move from "draft" to "submitted" |
| Drift | An AI slowly forgetting its rules over a long conversation | A new employee slowly ignoring the handbook |
| Hallucination | The AI stating something made-up as fact | Guessing instead of checking |
| Prompt caching | The AI provider reusing an unchanged prompt start, so it's cheaper and faster | Not re-reading the same intro every time |
| Working / short-term memory | What the AI holds for the current call: the context window | A notepad |
| Episodic memory | Long-term memory of what happened | A shift log |
| Semantic memory | Long-term memory of what is true: facts, policies, records | A policy binder |
| Procedural memory | Long-term memory of how to do things: rules, workflows, tools | The checklist taped to the wall |

## How a chat turn flows, and where state lives

One AI Assist question goes through `assist.ask()` → a LangGraph graph `gate → agent → check → finish`, saved by a checkpointer after each step. The case itself moves through `state.transition()`. Each group below follows one part of the chapter, starting with the Intro (the title links to its section). Each group shows **the book's problems in its order**, then **the book's solutions in its order**, built or not. **Names highlighted in yellow come from the book**; NurseOps Now's own extras follow, marked _(ours)_. "What happens" is the strategy; "How we check it" is the proof; **Details** links to the step that explains it, or to the plan if it isn't built.

This post uses [four memory types](#context-and-state-management-intro): working, episodic, semantic and procedural. They're defined in the Intro, and each problem and solution from there on is tagged with one, like `[Working]`.

**The 4 Agentic Outcomes: what the chapter sets out to achieve.** The book lists four goals up front; each starts with the problems it solves (click to jump to them, hover for a meaning), then the goal quoted exactly (highlighted in yellow), then my words. Each one is built from the solutions in one or two of its sections; hover a section link to see what it covers, click to jump there.

{#outcome-1}**1.** Problems: [The token window is a hard limit](#prob-the-token-window-is-a-hard-limit), [Cost and latency](#prob-cost-and-latency), [History can't keep growing](#prob-history-can-t-keep-growing) → **Engineer token budgets using progressive summarization and compression techniques to maximize the context window.** 🟡 In my words: keep every call within a planned size by shrinking old history. From [7.1 Short-term memory](#implementing-short-term-memory-token-budgets-and-window-management-7-1) and [7.2 Compression](#compression-strategies-summarization-and-entity-extraction-7-2). NurseOps Now caps history at 10 turns; no token count or summaries yet.

Book solutions behind it (click a name to jump to its row below, which links to the deep dive; hover for a one-line meaning):

- [Token Counting Middleware](#sol-token-counting-middleware) ⬜: count tokens before each call and act at set limits; NurseOps Now counts turns instead (7.1)
- [Textual Summarization](#sol-textual-summarization) ⬜: rewrite old turns as short notes (7.2)
- [Rolling Summaries](#sol-rolling-summaries) ⬜: keep one running summary in place of old turns (7.2)
- [Entity Extraction](#sol-entity-extraction) ✅: pull exact facts out of the chat; NurseOps Now keeps them in SQL from the start (7.2)
- [The Engineering Trade-off: Fidelity vs. Capacity](#sol-engineering-trade-off-fidelity-vs-capacity) ✅: decide what may be shortened and what must stay exact (7.2)

{#outcome-2}**2.** Problems: [LLMs are stateless](#prob-llms-are-stateless), [Flooding the context window](#prob-flooding-the-context-window) → **Architect hybrid memory systems that couple short-term conversational buffers with long-term Vector DB retrieval (RAG).** ✅ In my words: send the recent chat, and search stored knowledge only when needed. From [7.1 Short-term memory](#implementing-short-term-memory-token-budgets-and-window-management-7-1) and [7.3 Long-term memory](#implementing-long-term-memory-external-persistence-architecture-7-3). NurseOps Now sends the last 10 turns and searches policies and the guide with RAG tools.

Book solutions behind it (click a name to jump to its row below, which links to the deep dive; hover for a one-line meaning):

- [Dynamic Context Loading](#sol-dynamic-context-loading) ✅: the AI fetches the case, policy or guide with a tool only when needed (7.1)
- [Vector Compression via RAG](#sol-vector-compression-via-rag) 🟡: store text as vectors and pull back only what matches; documents only, not old chat (7.2)
- [The Hot/Cold State Architecture](#sol-hot-cold-state-architecture) ✅: the current call is hot, saved data is cold (7.3)
- [Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)](#sol-semantic-storage-vector-db) ✅: Chroma holds the policy text and the user guide (7.3)

{#outcome-3}**3.** Problems: [No external state](#prob-no-external-state), [Summarization solves volume, not time](#prob-summarization-solves-volume-not-time), [Persistence creates liability](#prob-persistence-creates-liability) → **Implement strict state serialization to allow agents to pause, crash, and resume without data loss.** 🟡 In my words: save progress after every step so a restart picks up where it left off. From [7.3 Long-term memory](#implementing-long-term-memory-external-persistence-architecture-7-3). Chat threads are checkpointed after every step; a case review reruns from the start after a crash.

Book solutions behind it (click a name to jump to its row below, which links to the deep dive; hover for a one-line meaning):

- [Structured Storage (SQL/Postgres)](#sol-structured-storage-sql-postgres) ✅: case facts and status as exact SQL records (7.3)
- [Session Caching (Redis/Key-Value)](#sol-session-caching-redis-key-value) ✅: each chat thread checkpointed after every step, in SQLite not Redis (7.3)
- [The Rehydration Pattern](#sol-rehydration-pattern) ✅: load the saved thread and only the facts needed back into the next call (7.3)
- [Sanitization layer](#sol-sanitization-layer) ✅: mask personal details before anything is saved (7.3)
- [TTL (time-to-live) expiration](#sol-ttl-expiration) ⬜: delete saved chat automatically after a set time (7.3)
- [GDPR Right to Be Forgotten](#sol-gdpr-right-to-be-forgotten) 🟡: clear a conversation on request, with an audit row (7.3)

{#outcome-4}**4.** Problems: [Loss of instructional integrity](#prob-loss-of-instructional-integrity), [Context Drift (The Alignment Failure)](#prob-context-drift-the-alignment-failure) → **Immunize against context drift by systematically pruning irrelevant dialogue and re-injecting core instructions.** 🟡 In my words: drop chat that no longer matters and resend the rules, so a long chat can't wear them down. From [7.4 Drift and hallucinations](#preventing-drift-and-hallucinations-in-long-running-agents-7-4). The rules are re-sent on every call and old turns are dropped from the window; an end-of-prompt reminder and a 50-turn drift test aren't built yet.

Book solutions behind it (click a name to jump to its row below, which links to the deep dive; hover for a one-line meaning):

- [System Prompt Pinning](#sol-system-prompt-pinning) ✅: the rules go in the system field on every call, so they're never trimmed (7.1)
- [Engineering Fix: Recursive Goal Injection](#sol-recursive-goal-injection) 🟡: repeat the rules near the end of the prompt; NurseOps Now re-sends them at the start only (7.4)
- [Input Filtering: Relevance Pruning](#sol-input-filtering-relevance-pruning) ✅: check and trim each question before the AI sees it (7.4)
- [Engineering Fix: Strict RAG and Citation Enforcement](#sol-strict-rag-and-citation-enforcement) ✅: against hallucination, the other half of 7.4: answer only from sources, flag any answer without one
- [Process Control: Self-Correction Loop](#sol-self-correction-loop) ✅: against hallucination: check the answer and send it back once to fix it (7.4)
- [Output Guardrails: Schema Enforcement](#sol-schema-enforcement) ✅: against hallucination: the answer must match a fixed shape, checked in code (7.4)

**In plain terms:** four promises for an AI's memory: stay on budget, remember both the chat and the facts, never lose your place, and never forget the rules.

**[Context and State Management (Intro)](#context-and-state-management-intro)**

**Problems** (the book's, in its order):

| # | Problem | What goes wrong | How NurseOps Now handles it | Solved by |
|---|---|---|---|---|
| 1 | {#prob-llms-are-stateless}**LLMs are stateless** [↑ Back to outcome 2](#outcome-2) | The model remembers nothing between calls; everything must be sent again every time | Every call is built fresh from saved state: the rules, the thread's last turns, and facts from tools | Three-tier memory, Hybrid memory systems ([Step 1](#step-1-pick-and-load-the-thread), [Step 2](#step-2-build-the-window)) |
| 2 | **The context window: finite, expensive, volatile** | The window has a size limit, every token costs money, and it's gone after the call | Small window per call; tokens and cost recorded for every call; nothing important lives only in the window | Token budgets ([Step 2](#step-2-build-the-window), [Step 8](#step-8-reuse-instead-of-recompute)) |
| 3 | {#prob-flooding-the-context-window}**Flooding the context window** [↑ Back to outcome 2](#outcome-2) | Too much raw data, and the AI forgets its original instructions | Rules in the separate system field; facts fetched on demand and capped | Token budgets; see the 7.1 table below ([Step 2](#step-2-build-the-window), [Step 3](#step-3-load-facts-only-when-needed)) |
| 4 | {#prob-no-external-state}**No external state** [↑ Back to outcome 3](#outcome-3) | When the script ends, the AI has forgotten everything | Chat checkpointed to disk per thread; case facts in SQL | Strict state serialization; see the 7.3 table below ([Step 1](#step-1-pick-and-load-the-thread), [Step 4](#step-4-hard-state-stays-in-sql)) |

**Solutions** (the book's concepts first, in its order, then ours):

| Solution | What happens in NurseOps Now | How we check it | Built? | Details | Deep dive |
|---|---|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | The window rebuilt on every call: rules, last 10 turns, a one-line case note | Demo: 12 turns stored, 10 sent | ✅ | [Step 2](#step-2-build-the-window) | [Deep dive](deep-dives/state-01-short-term-context-window.html) |
| **Three-Tier Memory: Long-Term (Vector Store)** | Chroma for policy text and the user guide; plus SQL for case facts and checkpoints for chat | Unit tests (RAG, memory) | ✅ | [Step 1](#step-1-pick-and-load-the-thread), [Step 4](#step-4-hard-state-stays-in-sql), [Ingestion deep dive](deep-dives/01-ingestion.html) | [Deep dive](deep-dives/state-02-long-term-vector-store.html) |
| **Three-Tier Memory: Episodic (Experience Log)** | `audit_log` table (every status change, AI Assist question and clear) and LangSmith traces | Unit test (audit row) | ✅ | [Step 7](#step-7-case-state-machine), [Step 9](#step-9-forget-on-request) | [Deep dive](deep-dives/state-03-episodic-experience-log.html) |
| **Agentic Outcome: Token Budgets** | A 10-turn history cap; no token count or summaries yet | Demo | 🟡 | [Step 2](#step-2-build-the-window), [Plan 1](#plan-closing-the-gaps), [Plan 2](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-04-token-budgets.html) |
| **Agentic Outcome: Hybrid Memory Systems** | Short-term buffer (last 10 turns) plus long-term retrieval (RAG tools over policies and the guide) | Unit tests (tool loop, RAG) | ✅ | [Step 2](#step-2-build-the-window), [Step 3](#step-3-load-facts-only-when-needed) | [Deep dive](deep-dives/state-05-hybrid-memory-systems.html) |
| **Agentic Outcome: Strict State Serialization** | Chat threads checkpointed after every step and reloaded after a restart; a case review isn't checkpointed mid-run, so a crash reruns it | Unit test (memory per user, restart, clear) | 🟡 Chat yes, review reruns | [Step 1](#step-1-pick-and-load-the-thread), [Findings](#findings-what-the-demos-showed) | [Deep dive](deep-dives/state-06-strict-state-serialization.html) |
| The one rule: case facts never in the chat _(ours)_ | Status, decisions and the AI review are SQL records; the AI looks them up fresh every time | Unit tests (state machine) | ✅ | [Step 4](#step-4-hard-state-stays-in-sql) | — |

**[Implementing Short-Term Memory: Token Budgets and Window Management (7.1)](#implementing-short-term-memory-token-budgets-and-window-management-7-1)**

**Problems** (the book's, in its order; the book describes them in paragraphs, not headings):

| # | Problem | What goes wrong | How NurseOps Now handles it | Solved by |
|---|---|---|---|---|
| 1 | {#prob-the-token-window-is-a-hard-limit}**The token window is a hard limit** [↑ Back to outcome 1](#outcome-1) | The rules, the question and the whole history all share one fixed budget | The window is rebuilt on every call with only what's needed: the rules, the last 10 turns and a one-line case note; facts come from tools | Dynamic Context Loading, History cap ([Step 2](#step-2-build-the-window), [Step 3](#step-3-load-facts-only-when-needed)) |
| 2 | **Sliding window truncation** | When the window fills, chat frameworks silently drop the oldest messages | NurseOps Now never sends more than the last 10 turns, so nothing is dropped behind its back; older turns stay saved on disk | History cap ([Step 2](#step-2-build-the-window), [Step 5](#step-5-older-turns)) |
| 3 | {#prob-loss-of-instructional-integrity}**Loss of instructional integrity** [↑ Back to outcome 4](#outcome-4) | The rules get pushed out (for example by a long pasted document), and the AI forgets its role | The rules are in the API's separate system field on every call; a question is cut at 2,000 characters and each tool result at 12,000 | System Prompt Pinning, Dynamic Context Loading ([Step 2](#step-2-build-the-window), [Step 3](#step-3-load-facts-only-when-needed)) |
| 4 | **Worse answers near capacity** | In a very full window, details in the middle get missed and the end gets too much weight | The window stays small, so it's never near capacity; there's no token check to prove it yet | History cap; Token Counting Middleware ⬜ ([Plan 1](#plan-closing-the-gaps)) |
| 5 | {#prob-cost-and-latency}**Cost and latency** [↑ Back to outcome 1](#outcome-1) | A full window is slower and costs more, because every token is paid for | Small window; identical reviews reused; review calls prompt-cached; tokens and cost recorded for every call | History cap, Reuse instead of recompute ([Step 8](#step-8-reuse-instead-of-recompute), [Plan 4](#plan-closing-the-gaps)) |

**Solutions** (the book's first, in its order, then ours):

| Solution | What happens in NurseOps Now | How we check it | Built? | Details | Deep dive |
|---|---|---|---|---|---|
| {#sol-token-counting-middleware}**Token Counting Middleware** [↑ Back to outcome 1](#outcome-1) | Count tokens before each call and act when the window gets too full | — | ⬜ Not built | [Plan 1](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-07-token-counting-middleware.html) |
| {#sol-dynamic-context-loading}**Dynamic Context Loading** [↑ Back to outcome 2](#outcome-2) | Case, policy, guide and metrics come from tools only when the AI asks; each result capped at 12,000 characters; at most 4 tool rounds | Unit test (tool loop) | ✅ | [Step 3](#step-3-load-facts-only-when-needed) | [Deep dive](deep-dives/state-08-dynamic-context-loading.html) |
| {#sol-system-prompt-pinning}**System Prompt Pinning** [↑ Back to outcome 4](#outcome-4) | The rules go in the API's separate system field on every call, never in the history, so they can't be trimmed | Demo | ✅ | [Step 2](#step-2-build-the-window) | [Deep dive](deep-dives/state-09-system-prompt-pinning.html) |
| One thread per user and case _(ours)_ | Each user + case has its own saved thread (`nurse1:case-3`), loaded from disk | Unit test (memory per user, restart, clear) | ✅ | [Step 1](#step-1-pick-and-load-the-thread) | — |
| History cap _(ours)_ | Only the last 10 turns are sent, plus a one-line note about the open case | Demo: 12 turns stored, 10 sent | ✅ | [Step 2](#step-2-build-the-window) | — |

**[Compression Strategies: Summarization and Entity Extraction (7.2)](#compression-strategies-summarization-and-entity-extraction-7-2)**

**Problems** (the book's, in its order):

| # | Problem | What goes wrong | How NurseOps Now handles it | Solved by |
|---|---|---|---|---|
| 1 | {#prob-history-can-t-keep-growing}**History can't keep growing** [↑ Back to outcome 1](#outcome-1) | You can't keep appending history: the window fills and every call gets more expensive | Exact facts never go into the chat; only the last 10 turns are sent; older turns stay on disk | Entity Extraction (a different way), History cap ([Step 4](#step-4-hard-state-stays-in-sql), [Step 5](#step-5-older-turns)) |
| 2 | **Hallucination drift** | Summaries are lossy: a summary of a summary drifts further each time, and exact details get corrupted | Nothing is summarized; IDs, dates, decisions and errors are stored word for word | The Engineering Trade-off: Fidelity vs. Capacity ([Step 4](#step-4-hard-state-stays-in-sql)) |

**Solutions** (the book's first, in its order, then ours):

| Solution | What happens in NurseOps Now | How we check it | Built? | Details | Deep dive |
|---|---|---|---|---|---|
| {#sol-textual-summarization}**Textual Summarization** [↑ Back to outcome 1](#outcome-1) | Rewrite old chat into dense notes | — | ⬜ Not built | [Step 5](#step-5-older-turns), [Plan 2](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-10-textual-summarization.html) |
| {#sol-rolling-summaries}**Rolling Summaries** [↑ Back to outcome 1](#outcome-1) | Every few turns, condense the oldest turns into a short summary | — | ⬜ Not built | [Step 5](#step-5-older-turns), [Plan 2](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-11-rolling-summaries.html) |
| {#sol-entity-extraction}**Entity Extraction** [↑ Back to outcome 1](#outcome-1) | Key facts in a structured record. Here: case fields, the AI review JSON and decisions are SQL records, fetched by a tool (not a JSON profile in the prompt) | State machine tests | ✅ (a different way) | [Step 4](#step-4-hard-state-stays-in-sql) | [Deep dive](deep-dives/state-12-entity-extraction.html) |
| {#sol-vector-compression-via-rag}**Vector Compression via RAG** [↑ Back to outcome 2](#outcome-2) | Embed past text and pull back only the relevant parts. Here: used for policy text and the user guide, not for chat history | Unit tests (RAG) | 🟡 Documents only | [Ingestion deep dive](deep-dives/01-ingestion.html) | [Deep dive](deep-dives/state-13-vector-compression-via-rag.html) |
| {#sol-engineering-trade-off-fidelity-vs-capacity}**The Engineering Trade-off: Fidelity vs. Capacity** [↑ Back to outcome 1](#outcome-1) | Summaries are lossy and drift, so exact facts ("hard state": IDs, numbers, decisions, code, error logs) are kept word for word and only conversation ("soft state") may be compressed. Here: exact facts are never in the chat at all, and nothing is summarized: reviews, decisions, audit rows and tool errors are stored as-is | — | ✅ | [Step 4](#step-4-hard-state-stays-in-sql) | [Deep dive](deep-dives/state-14-engineering-trade-off-fidelity-vs-capacity.html) |
| Old turns kept, not sent _(ours)_ | Turns beyond the last 10 stay on disk but leave the window | Demo: oldest sent is question 3 | ✅ | [Step 5](#step-5-older-turns) | — |

**[Implementing Long-Term Memory: External Persistence Architecture (7.3)](#implementing-long-term-memory-external-persistence-architecture-7-3)**

**Problems** (the book's, in its order):

| # | Problem | What goes wrong | How NurseOps Now handles it | Solved by |
|---|---|---|---|---|
| 1 | {#prob-summarization-solves-volume-not-time}**Summarization solves volume, not time** [↑ Back to outcome 3](#outcome-3) | A crash or a closed tab loses the window, however well it was summarized | Each chat thread is checkpointed to disk after every step; case state is in SQL | Session Caching, Structured Storage, The Rehydration Pattern ([Step 1](#step-1-pick-and-load-the-thread), [Step 7](#step-7-case-state-machine)) |
| 2 | {#prob-persistence-creates-liability}**Persistence creates liability** [↑ Back to outcome 3](#outcome-3) | Saved memory, logs and vector stores can leak personal data or secrets, and keep them forever | Personal details masked before saving; one thread can be deleted on request; no automatic expiry yet | Sanitization layer, GDPR Right to Be Forgotten, TTL expiration ⬜ ([Step 6](#step-6-mask-then-save-the-turn), [Step 9](#step-9-forget-on-request), [Plan 3](#plan-closing-the-gaps)) |

**Solutions** (the book's first, in its order, then ours):

| Solution | What happens in NurseOps Now | How we check it | Built? | Details | Deep dive |
|---|---|---|---|---|---|
| {#sol-hot-cold-state-architecture}**The Hot/Cold State Architecture** [↑ Back to outcome 2](#outcome-2) | Hot = what's in the current call; cold = SQL, checkpoints and Chroma | — | ✅ | [Step 1](#step-1-pick-and-load-the-thread), [Intro](#context-and-state-management-intro) | [Deep dive](deep-dives/state-15-hot-cold-state-architecture.html) |
| {#sol-structured-storage-sql-postgres}**Structured Storage (SQL/Postgres)** [↑ Back to outcome 3](#outcome-3) | SQLite tables `cases`, `ai_reviews`, `decisions`, `audit_log` | Unit tests (state machine) | ✅ | [Step 4](#step-4-hard-state-stays-in-sql) | [Deep dive](deep-dives/state-16-structured-storage-sql-postgres.html) |
| {#sol-semantic-storage-vector-db}**Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** [↑ Back to outcome 2](#outcome-2) | Chroma holds the policy text and the user guide | Unit tests (RAG) | ✅ | [Ingestion deep dive](deep-dives/01-ingestion.html) | [Deep dive](deep-dives/state-17-semantic-storage-vector-db.html) |
| {#sol-session-caching-redis-key-value}**Session Caching (Redis/Key-Value)** [↑ Back to outcome 3](#outcome-3) | LangGraph `SqliteSaver` checkpoints each thread after every step (SQLite instead of Redis) | Unit test (memory per user, restart, clear) | ✅ (SQLite, not Redis) | [Step 1](#step-1-pick-and-load-the-thread) | [Deep dive](deep-dives/state-18-session-caching-redis-key-value.html) |
| {#sol-rehydration-pattern}**The Rehydration Pattern** [↑ Back to outcome 3](#outcome-3) | Fetch the thread by ID, filter to the last 10 turns, inject them with the rules; facts come from tools | Demo | ✅ | [Step 1](#step-1-pick-and-load-the-thread), [Step 2](#step-2-build-the-window), [Step 3](#step-3-load-facts-only-when-needed) | [Deep dive](deep-dives/state-19-rehydration-pattern.html) |
| {#sol-sanitization-layer}**Sanitization layer** [↑ Back to outcome 3](#outcome-3) _(book's security paragraph, no heading)_ | Personal details masked before saving to memory, logs and traces | Demo: DOB, phone, SSN masked | ✅ | [Step 6](#step-6-mask-then-save-the-turn) | [Deep dive](deep-dives/state-20-sanitization-layer.html) |
| {#sol-ttl-expiration}**TTL (time-to-live) expiration** [↑ Back to outcome 3](#outcome-3) _(same paragraph)_ | Delete saved data automatically after a set time | — | ⬜ Not built | [Step 9](#step-9-forget-on-request), [Plan 3](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-21-ttl-expiration.html) |
| {#sol-gdpr-right-to-be-forgotten}**GDPR Right to Be Forgotten** [↑ Back to outcome 3](#outcome-3) _(same paragraph)_ | "Clear" deletes one thread and writes an audit row | Demo + test | 🟡 On request only | [Step 9](#step-9-forget-on-request) | [Deep dive](deep-dives/state-22-gdpr-right-to-be-forgotten.html) |
| Case state machine _(ours)_ | Status changes only along allowed paths; only a person can approve, deny or pend; every change audited | Unit tests (state machine) | ✅ | [Step 7](#step-7-case-state-machine) | — |
| Reuse instead of recompute _(ours)_ | Identical reviews reused from a result cache; review calls use prompt caching | Code | 🟡 Not for AI Assist | [Step 8](#step-8-reuse-instead-of-recompute), [Plan 4](#plan-closing-the-gaps) | — |

**[Preventing Drift and Hallucinations in Long-Running Agents (7.4)](#preventing-drift-and-hallucinations-in-long-running-agents-7-4)**

**Problems** (the book's, in its order, with its headings):

| # | Problem | What goes wrong | How NurseOps Now handles it | Solved by |
|---|---|---|---|---|
| 1 | {#prob-context-drift-the-alignment-failure}**Context Drift (The Alignment Failure)** [↑ Back to outcome 4](#outcome-4) | Over many turns the rules fade and the AI bends to the user (a strict reviewer slowly turns agreeable). Cause: the early rules get less attention as the conversation grows | The rules are sent on every call; bad questions are blocked in code; and no conversation can produce an approval, because the state machine only lets a person approve | Engineering Fix: Recursive Goal Injection 🟡, System Prompt Pinning, Input Filtering, Case state machine ([Step 2](#step-2-build-the-window), [Step 7](#step-7-case-state-machine), [Step 10](#step-10-gate-the-input-and-output), [Plan 5](#plan-closing-the-gaps)) |
| 2 | **Hallucination (The Grounding Failure)** | The AI fills a gap with something plausible and made-up. Cause: a high temperature, or the answer simply isn't in the context | Answers come only from tools; no source → a "please check" note; every review quote must match the PDF, with one retry; the output must match a schema | Engineering Fix: Strict RAG and Citation Enforcement, Process Control: Self-Correction Loop, Output Guardrails: Schema Enforcement ([Step 11](#step-11-ground-every-answer)) |

**Solutions** (the book's first, in its order, then ours):

| Solution | What happens in NurseOps Now | How we check it | Built? | Details | Deep dive |
|---|---|---|---|---|---|
| {#sol-recursive-goal-injection}**Engineering Fix: Recursive Goal Injection** [↑ Back to outcome 4](#outcome-4) | A short reminder of the rules before every answer. Here: the full rules are sent on every call, but there's no extra reminder at the end | — | 🟡 | [Step 2](#step-2-build-the-window), [Plan 5](#plan-closing-the-gaps) | [Deep dive](deep-dives/state-23-recursive-goal-injection.html) |
| {#sol-strict-rag-and-citation-enforcement}**Engineering Fix: Strict RAG and Citation Enforcement** [↑ Back to outcome 4](#outcome-4) | Answer only from tool results; no source → a "please check" note; review quotes must match the PDF | Unit test (quote check + retry) | ✅ | [Step 11](#step-11-ground-every-answer) | [Deep dive](deep-dives/state-24-strict-rag-and-citation-enforcement.html) |
| {#sol-input-filtering-relevance-pruning}**Input Filtering: Relevance Pruning** [↑ Back to outcome 4](#outcome-4) | Injection and off-topic questions blocked in code before the AI sees them (rules, not a second model) | Unit tests + red team (44 attacks, 0 through) | ✅ | [Step 10](#step-10-gate-the-input-and-output) | [Deep dive](deep-dives/state-25-input-filtering-relevance-pruning.html) |
| {#sol-self-correction-loop}**Process Control: Self-Correction Loop** [↑ Back to outcome 4](#outcome-4) | Reviews go `ai_review → verify`; a failed quote check sends the AI back once with the failures | Unit test (quote check + retry) | ✅ Reviews | [Step 11](#step-11-ground-every-answer) | [Deep dive](deep-dives/state-26-self-correction-loop.html) |
| {#sol-schema-enforcement}**Output Guardrails: Schema Enforcement** [↑ Back to outcome 4](#outcome-4) | Every review must match the `ReviewResult` Pydantic schema (shape, not truth) | Review tests | ✅ | [Step 11](#step-11-ground-every-answer) | [Deep dive](deep-dives/state-27-schema-enforcement.html) |
| Output gate _(ours)_ | Answers that quote the system prompt or contain a secret are blocked | Demo: prompt leak blocked | ✅ | [Step 10](#step-10-gate-the-input-and-output) | — |
| Long-conversation drift test _(ours)_ | A 50-turn scripted chat that keeps pushing for an approval | — | ⬜ Not built | [Plan 5](#plan-closing-the-gaps) | — |

The review of a case uses Steps 3, 4, 7, 8 and 11. A chat question uses Steps 1–3, 5, 6 and 9–11.

**About the examples below:** nurses ask AI Assist questions in a fresh, separate copy of the app (temporary database and memory file) on Nov 19, 2026. AI mode is **mock** (rules answer instead of Claude), so there is no API cost and no real data. The memory, masking, window and state code is the same code that runs with Claude.

## Context and State Management (Intro)

**The problem.** A language model is stateless: it remembers nothing between calls. Whatever the AI should know (the rules, the conversation so far, the case facts) has to be sent again on every call, inside the context window. That window is limited in size, paid for by the token, and gone as soon as the call ends. An app can fail in two opposite ways:

- **Too much in the window.** The call gets slow and expensive, and the rules sent at the start get less attention, so the AI can lose its instructions.
- **Nothing saved outside it.** After a restart, a crash or a new session, the AI starts from zero.

**The four memory types.** AI memory is grouped the way human memory is: one short-term type and three long-term ones.

| Type | What it holds | Where it lives | In NurseOps Now |
|---|---|---|---|
| **Working / Short-term** | The live task: rules, recent turns, tool results for this call | The context window | Rules + last 10 turns + one-line case note, rebuilt every call |
| **Episodic** (long-term) | What happened: dated events, past sessions, mistakes | Event logs, chat history | `audit_log`, LangSmith traces, LangGraph checkpoints per thread |
| **Semantic** (long-term) | What is true: facts, policies, records | Vector DB, SQL tables | Chroma (policy text, user guide), SQL case facts |
| **Procedural** (long-term) | How to do things: rules, workflows, steps | Code, system prompts, tool definitions, state machines | System prompt, tool definitions, case state machine |

The chapter names three tiers (short-term, long-term, episodic). This post splits long-term into the three types it actually holds. Each problem and solution below is tagged with the type it deals with, for example `[Working]`; an item that moves memory from one type into another gets both tags.

**In plain terms:** a nurse's notepad (working), shift log (episodic), policy binder (semantic) and the checklist taped to the wall (procedural).

**How NurseOps Now solves it.**

- `[Working]` **Working / short-term:** a small window rebuilt on every call: the rules, the last 10 turns and a one-line note about the open case. See [the short-term memory section](#implementing-short-term-memory-token-budgets-and-window-management-7-1).
- `[Episodic · Semantic]` **Long-term:** LangGraph checkpoints for each chat thread (episodic); SQL for case facts and Chroma for policy text (semantic). See [the long-term memory section](#implementing-long-term-memory-external-persistence-architecture-7-3).
- `[Episodic]` **Episodic:** the `audit_log` table (every status change, AI Assist question and clear) and LangSmith traces of each call.
- `[Procedural]` **Rules and workflow:** the system prompt sent on every call, the tool definitions, and the case state machine that only lets a person approve. See [Step 2](#step-2-build-the-window) and [Step 7](#step-7-case-state-machine).
- `[Semantic]` **The one rule behind everything:** case facts are never kept in the chat. Status, decisions, missing items and the AI review are stored in SQL as exact records. The chat only remembers the conversation, with personal details masked, and the AI looks the facts up fresh with a tool every time.

**In plain terms:** a nurse with a notepad and a filing cabinet. The notepad holds the last few things said and gets recycled; the filing cabinet holds the official case file, which is never rewritten from memory.

### With LangGraph, AutoGen, CrewAI and LlamaIndex (Intro)

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's 6 solutions, 4 are mostly replaced by the frameworks, 0 stay mostly yours, and the others are used together.

| Book solution | Overall | [LangGraph](deep-dives/fw-langgraph.html) | [AutoGen](deep-dives/fw-autogen.html) | [CrewAI](deep-dives/fw-crewai.html) | [LlamaIndex](deep-dives/fw-llamaindex.html) |
|---|---|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | 🔁 / 🤝 | 🤝 Messages live in graph state per thread; you trim them with `trim_messages` | 🔁 The agent's model context: `BufferedChatCompletionContext`, `TokenLimitedChatCompletionContext`, `HeadAndTailChatCompletionContext` | 🤝 Recalled memories are injected before each task; no chat-window setting on the memory page | 🔁 `Memory.from_defaults(session_id=..., token_limit=...)` manages the chat history |
| **Three-Tier Memory: Long-Term (Vector Store)** | 🔁 Replace (for agent memory) | 🔁 Store (`InMemoryStore`, `PostgresStore`, …) with semantic search, per namespace | 🔁 `ChromaDBVectorMemory`, `RedisMemory`, `Mem0Memory` | 🔁 Unified `Memory`: `remember` / `recall` with semantic search (LanceDB by default) | 🔁 `VectorMemoryBlock` on any vector store |
| **Three-Tier Memory: Episodic (Experience Log)** | 🤝 Complement | 🤝 `get_state_history` replays a thread's checkpoints; the audit log is yours | 🤝 `ListMemory` keeps a chronological list; the audit log is yours | 🤝 Memory records carry `source` and time; the audit log is yours | 🤝 The chat store keeps messages per session; the audit log is yours |
| **Agentic Outcome: Token Budgets** | 🤝 Complement | 🤝 `trim_messages(max_tokens=...)`; the budget per zone is yours | 🔁 `TokenLimitedChatCompletionContext(token_limit=...)` (experimental) | 🛠 Not on the memory page | 🔁 `token_limit`, `chat_history_token_ratio` and block `priority` decide what's kept |
| **Agentic Outcome: Hybrid Memory Systems** | 🔁 Replace | 🔁 Checkpointer (short-term) + Store (long-term) in one graph | 🔁 Model context + `memory=[...]` on the agent | 🔁 One `Memory` recalled into every task | 🔁 Short-term chat + memory blocks in one `Memory` |
| **Agentic Outcome: Strict State Serialization** | 🔁 LangGraph, 🤝 others | 🔁 Checkpointers save after every step; resume with `invoke(None, config)`; `durability` modes | 🤝 `save_state()` / `load_state()` return a dict; storing it is yours | 🤝 Memory is persistent; saving a run's state isn't on the memory page | 🤝 Workflow `ctx.to_dict()` / `Context.from_dict()`; Memory is stored separately |

_Memory features checked against each framework's official memory docs on Nov 19, 2026. † = not a memory feature, so from general knowledge; check the current docs._

## Implementing Short-Term Memory: Token Budgets and Window Management (7.1)

**What it does.** Keeps each call's context window small and on budget: count tokens, load facts only when needed, and pin the rules so they're never pushed out.

**The problem** (the book's, in its order):

1. `[Working]` **The token window is a hard limit:** the rules, the question and the whole history share one fixed budget.
2. `[Working · Episodic]` **Sliding window truncation:** when it fills, chat frameworks silently drop the oldest messages.
3. `[Procedural]` **Loss of instructional integrity:** the rules can be pushed out, for example by a long pasted document, and the AI forgets its role.
4. `[Working]` **Worse answers near capacity:** in a very full window, details in the middle get missed.
5. `[Working]` **Cost and latency:** a full window is slower and costs more.

**How NurseOps Now solves it** (the chapter's three solutions first, in its order, then ours):

- `[Working]` **Token counting middleware** ⬜ not yet: nothing counts tokens before a call; the history cap below counts turns, not tokens ([Plan 1](#plan-closing-the-gaps)).
- `[Working · Semantic]` **Dynamic context loading** ✅: the AI fetches the case, policy or guide with a tool only when it needs them; each result is capped at 12,000 characters, with at most 4 tool rounds ([Step 3](#step-3-load-facts-only-when-needed)).
- `[Procedural]` **System prompt pinning** ✅: the rules go in the API's separate system field on every call, never in the history, so they can't be trimmed ([Step 2](#step-2-build-the-window)).
- `[Working]` **History cap** (ours, a simpler stand-in for a token budget) ✅: only the last 10 turns are sent ([Step 2](#step-2-build-the-window)).
- `[Episodic]` **One thread per user and case** (ours) ✅: windows never mix ([Step 1](#step-1-pick-and-load-the-thread)).

### With LangGraph, AutoGen, CrewAI and LlamaIndex (7.1)

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's 3 solutions, 2 are mostly replaced by the frameworks, 0 stay mostly yours, and the others are used together.

| Book solution | Overall | [LangGraph](deep-dives/fw-langgraph.html) | [AutoGen](deep-dives/fw-autogen.html) | [CrewAI](deep-dives/fw-crewai.html) | [LlamaIndex](deep-dives/fw-llamaindex.html) |
|---|---|---|---|---|---|
| **Token Counting Middleware** | 🤝 Complement | 🤝 `trim_messages` with a `token_counter`; thresholds and actions are yours | 🔁 `TokenLimitedChatCompletionContext` counts with `model_client.count_tokens()` | 🛠 Not on the memory page | 🔁 Counts tokens (tiktoken by default) and flushes old messages past the limit |
| **Dynamic Context Loading** † | 🔁 Replace | 🔁 Tools and tool nodes are standard | 🔁 Tools on `AssistantAgent` are standard | 🔁 Agent tools and knowledge sources are standard | 🔁 Tools and query engines are standard |
| **System Prompt Pinning** † | 🔁 / 🤝 | 🤝 You add the system prompt in your node, outside the trimmed history | 🤝 `HeadAndTailChatCompletionContext` can always keep the first messages | 🔁 Each agent's role, goal and backstory go into every task prompt | 🔁 `StaticMemoryBlock` with `priority=0` is always inserted, never truncated |

_Memory features checked against each framework's official memory docs on Nov 19, 2026. † = not a memory feature, so from general knowledge; check the current docs._

### Step 1: Pick and load the thread

**What it does.** Chooses which saved conversation this question belongs to, and loads it from disk.

**What we built.** `backend/app/services/assist.py`: one thread per user and case, saved by LangGraph's `SqliteSaver` in `backend/data/assist_memory.db`.

```python
def thread_id(user: str, case_id: int | None) -> str:
    return f"{user}:case-{case_id}" if case_id else f"{user}:general"
```

**Example (real output).** Three nurses' questions land in three separate threads, and they're still there after a restart:

```
thread nurse1:general     -> 4 messages
thread nurse2:general     -> 2 messages
thread nurse1:case-3      -> 2 messages
after a restart (new saver): nurse1:general -> 4 messages
```

**Why this way.** Per user + case is the smallest useful unit. Nurse 1's chat about case 3 never mixes with case 5, or with nurse 2's chat. Loading by thread ID is the chapter's rehydration pattern (fetch, then use), done by the checkpointer.

**How it's checked.** `test_memory_persists_per_user_and_case_and_clears` asks as two users, "restarts", and checks the counts.

**In plain terms:** one folder per nurse per case; you open only the folder you're working on.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 2: Build the window

**What it does.** Decides exactly what goes into the AI call: the rules, recent history, and a note about the open case.

**What we built.** `claude_answer()` in `assist.py`:

```python
system = load("assist_v1")                                    # rules: sent on every call, outside the history
msgs = [{"role": h["role"], "content": h["text"]} for h in history[-2 * settings.assist_turns:]]
ctx = f"(The user is looking at case {case_id}.) " if case_id else ""
msgs.append({"role": "user", "content": f"{ctx}{q}"})
```

**Example (real output).** One nurse asked 12 questions in a row:

```
stored 24 messages (12 turns); sent to the AI 20 messages (10 turns)
oldest stored : Question 1: who can deny a request? | oldest sent: Question 3: who can deny a request?
```

(In mock mode Claude isn't called, so "sent" is computed with the same line of code `claude_answer()` uses.)

**Why this way.**

- **The rules can't be pushed out.** The system prompt (`backend/app/prompts/assist_v1.md`) goes in the API's separate `system` field on every call, not into the history. However long the chat gets, the rules are always there. This is the chapter's **system prompt pinning**, and it's the fix for the chapter's main failure story.
- **A turn limit keeps the window small.** `ASSIST_TURNS` (default 10) caps how much history is sent.
- **The case is a short note, not a data dump.** "(The user is looking at case 3.)" tells the AI where to look; the facts come from a tool (Step 3).

**Trade-off.** The limit counts turns, not tokens. Ten very long turns could still be large. There is no **token counting middleware** before the call (see [Plan](#plan-closing-the-gaps)).

**In plain terms:** the handbook is always on the desk; only the last ten notes from the conversation are; the case file is fetched when needed.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 3: Load facts only when needed

**What it does.** Gives the AI tools to fetch case facts, policy text, the user guide and metrics, instead of putting them all in the prompt.

**What we built.** Read-only tools in `assist.py` (`get_case`, `list_cases`, `stuck_cases`, `metrics`, `search_policy`, `search_guide`) that call the same services as the web app. Two size guards:

```python
MAX_TOOL_ROUNDS = 4
...
results.append({"type": "tool_result", "tool_use_id": tu.id, "content": json.dumps(out, default=str)[:12000]})
```

**Why this way.** This is the chapter's **dynamic context loading**. The AI gets only what this question needs, and always the current version of the case, never an old copy from earlier in the chat. The 12,000-character cap stops one large tool result from flooding the window, a risk the chapter doesn't mention.

**How it's checked.** `test_claude_agent_uses_tools_then_answers` (mocked Claude) checks the tool loop and the answer.

**In plain terms:** instead of photocopying the whole cabinet onto the desk, the AI asks for one file at a time, and each file is trimmed to fit.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

## Compression Strategies: Summarization and Entity Extraction (7.2)

**What it does.** Shrinks history that can't keep growing: summarize old turns and pull exact facts out of the chat so they can't drift.

**The problem.** `[Episodic · Semantic]` History can't grow forever, so something has to be shrunk. But a summary loses detail, and a summary of a summary drifts further each time. That's harmless for small talk and dangerous for exact facts: an ID, a date or a decision that's slightly wrong is simply wrong.

**How NurseOps Now solves it.**

- `[Semantic]` **Exact facts are never in the chat at all:** they're SQL records, fetched fresh by a tool, so there's nothing to summarize wrongly ([Step 4](#step-4-hard-state-stays-in-sql)). That goes further than the chapter's idea of keeping key facts in a JSON profile.
- `[Working · Episodic]` **Old turns are kept, not sent:** turns beyond the last 10 stay on disk but leave the window ([Step 5](#step-5-older-turns)).
- `[Episodic]` **Not yet:** a short summary of older turns, so something a nurse said 11 turns ago isn't lost ([Plan 2](#plan-closing-the-gaps)).

### With LangGraph, AutoGen, CrewAI and LlamaIndex (7.2)

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's 5 solutions, 2 are mostly replaced by the frameworks, 2 stay mostly yours, and the others are used together.

| Book solution | Overall | [LangGraph](deep-dives/fw-langgraph.html) | [AutoGen](deep-dives/fw-autogen.html) | [CrewAI](deep-dives/fw-crewai.html) | [LlamaIndex](deep-dives/fw-llamaindex.html) |
|---|---|---|---|---|---|
| **Textual Summarization** | 🛠 Mostly yours | 🤝 LangMem `SummarizationNode`, or a custom `summary` key | 🛠 Not built in | 🤝 `extract_memories()` splits text into facts (not a summary) | 🛠 The summary buffer is deprecated; old messages are flushed to memory blocks instead |
| **Rolling Summaries** | 🤝 / 🛠 | 🤝 LangMem `SummarizationNode(max_tokens_before_summary=...)` | 🛠 Not built in | 🛠 Not built in | 🤝 Past `chat_history_token_ratio`, the oldest messages move to long-term blocks |
| **Entity Extraction** | 🔁 CrewAI and LlamaIndex, 🤝 others | 🤝 Write extracted facts to the Store yourself, or use LangMem | 🤝 `Mem0Memory` extracts facts (an outside service) | 🔁 `remember` analyzes content with an LLM (categories, importance); `extract_memories()` | 🔁 `FactExtractionMemoryBlock(max_facts=...)` |
| **Vector Compression via RAG** | 🔁 Replace | 🔁 Store semantic search over saved memories | 🔁 ChromaDB or Redis vector memory | 🔁 `recall(query)` over all saved memories | 🔁 Flushed messages go into a `VectorMemoryBlock` |
| **The Engineering Trade-off: Fidelity vs. Capacity** | 🛠 Still yours | 🛠 No hard/soft split; your exact facts belong in your own tables | 🛠 Same | 🛠 Consolidation can merge or delete records automatically: keep exact facts elsewhere | 🛠 Fact extraction is an LLM rewrite: keep exact facts elsewhere |

_Memory features checked against each framework's official memory docs on Nov 19, 2026. † = not a memory feature, so from general knowledge; check the current docs._

### Step 4: Hard state stays in SQL

**What it does.** Keeps every exact fact (status, decisions, the AI review, the audit trail) as records in the database, never as chat text.

**What we built.** `backend/app/models.py`: tables `cases`, `ai_reviews` (the review as JSON), `decisions`, `audit_log`. The chat never stores these; the AI reads them through `get_case`.

**Why this way.** The chapter warns that summaries drift, so exact facts (numbers, IDs, decisions) must be stored losslessly and only "soft" conversation may be compressed. NurseOps Now goes one step further: facts are never in the chat at all, so there is nothing to summarize wrongly.

**In plain terms:** the official file is typed, signed and filed; nobody rewrites it from memory.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 5: Older turns

**What it does.** Handles conversation older than the last 10 turns.

**What we built.** Nothing extra: older turns stay saved on disk (Step 1 example: question 1 is still stored) but are no longer sent to the AI.

**Why this way.** Because facts are looked up fresh (Steps 3–4), losing old chat turns rarely loses anything important. A nurse who asks again gets the current answer, not a stale one.

**Trade-off.** If a nurse said something important 11 turns ago ("I already called the provider"), the AI no longer sees it. The chapter's fixes, a rolling summary or a small profile of key facts, are not built. Saved history also keeps growing on disk.

**In plain terms:** old notes go into a drawer; they're kept, but nobody reads them during the meeting.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

## Implementing Long-Term Memory: External Persistence Architecture (7.3)

**What it does.** Saves state outside the model so it survives restarts, crashes and new sessions, without keeping personal data longer than needed.

**The problem.** `[Episodic · Semantic]` The window disappears after every call. Without a store outside the model, a restart, a crash or a new session loses everything. And whatever is saved becomes a liability: personal data copied into memory, logs and traces, and data kept forever.

**How NurseOps Now solves it.**

- `[Episodic]` **Chat survives restarts:** each thread is checkpointed to SQLite after every step ([Step 1](#step-1-pick-and-load-the-thread), [Step 6](#step-6-mask-then-save-the-turn)).
- `[Episodic]` **Personal details are masked before saving** ([Step 6](#step-6-mask-then-save-the-turn)).
- `[Semantic · Procedural]` **Case state lives in SQL** and moves only along allowed paths, with an audit row for every change ([Step 7](#step-7-case-state-machine)).
- `[Semantic]` **Work isn't paid for twice:** identical reviews are reused, and review calls use prompt caching ([Step 8](#step-8-reuse-instead-of-recompute)).
- `[Episodic]` **A conversation can be forgotten on request,** with an audit row ([Step 9](#step-9-forget-on-request)).
- `[Episodic]` **Not yet:** automatic expiry and a cap on stored history ([Plan 3](#plan-closing-the-gaps)); prompt caching for AI Assist ([Plan 4](#plan-closing-the-gaps)).

### With LangGraph, AutoGen, CrewAI and LlamaIndex (7.3)

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's 8 solutions, 2 are mostly replaced by the frameworks, 3 stay mostly yours, and the others are used together.

| Book solution | Overall | [LangGraph](deep-dives/fw-langgraph.html) | [AutoGen](deep-dives/fw-autogen.html) | [CrewAI](deep-dives/fw-crewai.html) | [LlamaIndex](deep-dives/fw-llamaindex.html) |
|---|---|---|---|---|---|
| **The Hot/Cold State Architecture** | 🤝 Complement | 🤝 Graph state is hot; checkpointers and the Store are cold; you decide what goes where | 🤝 Model context is hot; `Memory` and saved state are cold | 🤝 The prompt is hot; `Memory` is cold | 🤝 Short-term chat is hot; memory blocks are cold |
| **Structured Storage (SQL/Postgres)** | 🛠 Still yours | 🛠 `PostgresSaver` stores checkpoints, not your business tables | 🛠 None | 🛠 Memory is stored in LanceDB, not your records | 🛠 A SQL chat store holds messages, not your records |
| **Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** | 🔁 for agent memory, 🤝 for documents with permissions | 🔁 Store with an `index` (embeddings), many backends | 🔁 `ChromaDBVectorMemory`, `RedisMemory` | 🔁 LanceDB by default, or a custom `StorageBackend` | 🔁 `VectorMemoryBlock` on any LlamaIndex vector store |
| **Session Caching (Redis/Key-Value)** | 🔁 LangGraph and LlamaIndex | 🔁 Checkpointers incl. `RedisSaver`, keyed by `thread_id` | 🤝 `save_state()` gives a dict; you store it under your session key | 🛠 No session or thread concept (scopes instead) | 🔁 `session_id` with a SQL chat store (`async_database_uri`) |
| **The Rehydration Pattern** | 🤝 Complement | 🤝 Reload by `thread_id`, memories by namespace; filtering and injection are yours | 🤝 `load_state()`; memory adds relevant items to the context | 🔁 Relevant memories are recalled into each task, filtered by scope | 🔁 `memory.get()` returns recent chat plus memory blocks |
| **Sanitization layer** | 🛠 Still yours | 🛠 No redaction; `EncryptedSerializer` encrypts checkpoints at rest | 🛠 No redaction | 🛠 No redaction; `private` flag; docs suggest a local LLM for sensitive data | 🛠 Not on the memory page |
| **TTL (time-to-live) expiration** | 🛠 Still yours | 🛠 No built-in TTL in the docs; they suggest a cron job to delete old checkpoints | 🛠 Not mentioned | 🛠 Not built in; `recency_half_life_days` only affects ranking | 🛠 Not mentioned |
| **GDPR Right to Be Forgotten** | 🤝 Complement (covering every store is yours) | 🤝 `checkpointer.delete_thread(thread_id)`; Store items deleted by key | 🤝 `memory.clear()` clears a whole store, not one user | 🤝 `memory.reset(scope="/customer/...")` clears one scope | 🤝 Delete messages in the chat store by session |

_Memory features checked against each framework's official memory docs on Nov 19, 2026. † = not a memory feature, so from general knowledge; check the current docs._

### Step 6: Mask, then save the turn

**What it does.** Removes personal details from the question and answer, then saves the turn to the thread.

**What we built.** The graph's last node, `finish`, in `assist.py`, uses `backend/app/pii.py`:

```python
def finish(s):
    from app import pii                                      # S5: memory keeps no member names/IDs
    names = pii.case_names(session, s.get("case_id"))
    return {"history": [{"role": "user", "text": pii.redact(s["question"], names)},
                        {"role": "assistant", "text": pii.redact(s["answer"], names)}]}
```

**Example (real output).**

```
asked : Member DOB 04/12/1961, phone 555-201-3344, SSN 123-45-6789: what are the rules for a knee MRI?
stored: Member DOB [DATE], phone [PHONE], SSN [SSN]: what are the rules for a knee MRI?
```

**Why this way.** The chapter's point that saved state is a liability. Memory, logs and traces are copies that outlive the conversation, so they keep no member names, dates of birth, phone numbers, SSNs, member IDs or addresses. The case record itself stays complete (staff-only, audited). LangSmith traces also get a masked thread ID.

**Trade-off.** Pattern-based masking catches known formats and the names on the case; a name typed in an unusual way could slip through.

**In plain terms:** before filing your meeting notes, black out every personal detail.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 7: Case state machine

**What it does.** Lets a case's status change only along allowed paths, and only a person can approve, deny or pend.

**What we built.** `backend/app/services/state.py`:

```python
ALLOWED: dict[str, set[str]] = {
    RECEIVED: {INCOMPLETE, READY},
    INCOMPLETE: {RECEIVED},
    READY: {APPROVED, DENIED, PENDED},
    PENDED: {READY},
    APPROVED: {SYNCED},
    DENIED: {SYNCED},
    SYNCED: set(),
}
```

**Example (real output).**

```
Approved        human=False -> REFUSED: Approved can only be set by a human reviewer
ReadyForReview  human=False -> OK, status now ReadyForReview
Approved        human=False -> REFUSED: Approved can only be set by a human reviewer
Approved        human=True  -> OK, status now Approved
audit rows for this case: [('status_change', 'Received', 'ReadyForReview'), ('status_change', 'ReadyForReview', 'Approved')]
```

**Why this way.** This is long-term state the chapter only touches on: workflow state. It lives in SQL, is checked in code (not in the AI's prompt), and every change leaves an audit row. No conversation, however long, can talk the system into an approval.

**How it's checked.** `test_state.py`: allowed moves, human-only moves, every other move rejected, audit row written.

**In plain terms:** a form that physically can't be stamped "approved" unless a nurse signs it.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 8: Reuse instead of recompute

**What it does.** Avoids paying twice for the same AI work.

**What we built.** Two layers in `backend/app/llm/client.py`:

- **A result cache** (`llm_cache` table). A case review is reused when the documents, policy version, policy chunks, model and prompt version are all the same (`backend/app/services/review.py`). Retries after a failed check skip the cache.
- **Prompt caching** on review calls (`cache_control={"type": "ephemeral"}`), so the provider can reuse an unchanged prompt start.

**Why this way.** The chapter says a full window is slow and costly but doesn't mention caching, which is often the cheapest fix.

**Trade-off.** AI Assist calls (`create()`) don't ask for prompt caching yet, though their system prompt is the same on every call. Not demoed here: it needs real Claude calls.

**In plain terms:** if you've already reviewed this exact file, use your notes instead of reviewing it again.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 9: Forget on request

**What it does.** Deletes one conversation when the user clears it.

**What we built.** `assist.clear()` deletes the thread's checkpoints and writes an `assist_cleared` audit row.

**Example (real output).** Only the cleared thread is gone:

```
nurse1:general -> 0 | nurse1:case-3 -> 2 | nurse2:general -> 2
audit rows 'assist_cleared': 1
```

**Trade-off.** There is no automatic expiry: a thread nobody clears is kept forever. The chapter's time-to-live idea is not built.

**In plain terms:** shredding one folder, and noting in the log that you did.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

## Preventing Drift and Hallucinations in Long-Running Agents (7.4)

**What it does.** Keeps a long-running agent on its rules (no drift) and on the facts (no hallucination) by re-sending instructions and grounding every answer.

**The problem** (the book's, in its order):

1. `[Procedural]` **Context Drift (The Alignment Failure):** over many turns the rules fade and the AI starts bending to the user (a strict reviewer slowly becomes an agreeable helper).
2. `[Semantic]` **Hallucination (The Grounding Failure):** when the answer isn't in front of it, the AI fills the gap with something plausible and made-up.

**How NurseOps Now solves it.**

- `[Procedural]` **Against drift:** the rules are sent on every call ([Step 2](#step-2-build-the-window)); bad questions and leaky answers are blocked in code ([Step 10](#step-10-gate-the-input-and-output)); and no conversation can produce an approval, because the state machine only lets a person approve ([Step 7](#step-7-case-state-machine)).
- `[Semantic]` **Against hallucination:** answers come only from tools, an answer with no source gets a "please check" note, every review quote must match the PDF (with one retry), and the output must match a schema ([Step 11](#step-11-ground-every-answer)).
- `[Procedural]` **Not yet:** an extra reminder of the rules at the end of the prompt, and a 50-turn test that proves the AI doesn't drift ([Plan 5](#plan-closing-the-gaps)).

### With LangGraph, AutoGen, CrewAI and LlamaIndex (7.4)

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's 5 solutions, 1 is mostly replaced by the frameworks, 2 stay mostly yours, and the others are used together.

| Book solution | Overall | [LangGraph](deep-dives/fw-langgraph.html) | [AutoGen](deep-dives/fw-autogen.html) | [CrewAI](deep-dives/fw-crewai.html) | [LlamaIndex](deep-dives/fw-llamaindex.html) |
|---|---|---|---|---|---|
| **Engineering Fix: Recursive Goal Injection** † | 🤝 Complement | 🤝 Add the reminder in the node that builds the prompt | 🛠 Yours to add | 🤝 Role and goal in every task prompt act as an anchor | 🤝 A `StaticMemoryBlock` reminder is inserted every turn |
| **Engineering Fix: Strict RAG and Citation Enforcement** † | 🛠 Still yours | 🛠 Retrieval tools yes; checking citations is yours | 🛠 Yours | 🛠 Yours | 🤝 Citation-style query engines return numbered sources; checking them is yours |
| **Input Filtering: Relevance Pruning** † | 🛠 Still yours | 🤝 Add a gate node before the model (as NurseOps Now does) | 🛠 Yours | 🛠 Yours | 🛠 Yours |
| **Process Control: Self-Correction Loop** † | 🤝 Complement | 🤝 Conditional edges loop back to the model; the check is yours | 🤝 A second agent can review (reflection pattern) | 🤝 Task guardrails can reject output and retry | 🤝 Workflows can loop back; the check is yours |
| **Output Guardrails: Schema Enforcement** † | 🔁 Replace | 🔁 Structured output with a Pydantic model | 🔁 Structured output on `AssistantAgent` | 🔁 Task `output_pydantic` / `output_json` | 🔁 Structured output with a Pydantic `output_cls` |

_Memory features checked against each framework's official memory docs on Nov 19, 2026. † = not a memory feature, so from general knowledge; check the current docs._

### Step 10: Gate the input and output

**What it does.** Stops bad questions before the AI sees them, and bad answers before the user sees them.

**What we built.** The `gate` and `check` nodes in `assist.py`, using `backend/app/guard.py`: injection and off-topic checks in code (no AI call), and an output check that blocks secrets and any 80-character run of the system prompt.

**Example (real output).**

```
answer quoting 120 chars of the system prompt -> Blocked: prompt_leak
```

**Why this way.** The chapter's "filter the input" defense layer, done with rules instead of a second small model: free, fast and predictable. Together with Step 2 (rules always sent), it guards against the slow drift the chapter describes.

**How it's checked.** `test_assist.py` (injection blocked, off-topic gated, leaky answer blocked) and the red-team suite in the [eval plan](nurseops-now-evals.html#step-3-input-guardrails) (44 attacks, 0 got through).

**In plain terms:** a receptionist who turns away off-topic visitors, and a reviewer who checks every letter before it goes out.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

### Step 11: Ground every answer

**What it does.** Makes sure answers come from real data, not from the AI's guesses.

**What we built.**

- **AI Assist:** the prompt says answer only from tool results and say "I don't know" otherwise; the `check` node adds "(No source found for this answer: please check it.)" when an answer has no sources.
- **Case review:** `review_graph.py` runs `ai_review → verify`; every quote must match the PDF exactly, and a failed check sends Claude back once with the list of failures. The output must match the `ReviewResult` Pydantic schema.

**Why this way.** The chapter's "strict RAG and citation enforcement". One correction: the schema guarantees the answer's **shape**, not its **truth**. It's the quote check against the PDF that catches made-up content.

**How it's checked.** `test_failed_quote_retries_claude_once_with_feedback`, `test_no_retry_when_quotes_verify`.

**In plain terms:** every claim needs a page number, and someone checks the page.

[↑ Back to the flow](#how-a-chat-turn-flows-and-where-state-lives)

## The chapter vs. NurseOps Now

Every idea from the chapter's intro and its four parts, in my own words, with where NurseOps Now stands.

| Part | Idea | NurseOps Now | Status |
|---|---|---|---|
| Intro | Models are stateless; memory in tiers (the book names three: window, long-term store, episode log; this post uses four types) | Working = Step 2; episodic = checkpoints + `audit_log` + traces; semantic = SQL + Chroma; procedural = system prompt, tools, state machine | ✅ |
| Short-term memory (7.1) | Count tokens before each call; act at thresholds | Turn limit only | ⬜ |
| Short-term memory (7.1) | Load context only when needed | Tools (Step 3) | ✅ |
| Short-term memory (7.1) | Pin the system prompt | `system` field on every call (Step 2) | ✅ |
| Compression (7.2) | Rolling summaries of old turns | Old turns dropped from the window, not summarized (Step 5) | ⬜ |
| Compression (7.2) | Key facts in a structured profile | Facts in SQL, fetched by tool (Steps 3–4) | ✅ (different way) |
| Compression (7.2) | Never summarize exact facts | Facts never in chat at all (Step 4) | ✅ |
| Long-term memory (7.3) | Hot / cold state | Window vs. SQL, checkpoints, Chroma | ✅ |
| Long-term memory (7.3) | SQL for exact facts, vector store for fuzzy text, a session store for pause/resume | SQLite, Chroma, LangGraph checkpoints | ✅ |
| Long-term memory (7.3) | Rehydration: fetch, filter, inject | Thread load + last 10 turns + tools (Steps 1–3) | ✅ |
| Long-term memory (7.3) | Scrub personal data before saving | Step 6 | ✅ |
| Long-term memory (7.3) | Expire stored data automatically | Manual clear only (Step 9) | ⬜ |
| Drift and hallucinations (7.4) | Re-inject the goal against drift | Rules sent separately every call (Step 2), no extra reminder at the end | 🟡 |
| Drift and hallucinations (7.4) | Answer only with citations | Steps 10–11 | ✅ |
| Drift and hallucinations (7.4) | Input filter, self-check loop, output schema | Rule gate, verify-and-retry, Pydantic (Steps 10–11) | ✅ |

**What I'd correct in the chapter:**

- **"Old messages get silently deleted, including the rules."** That's what some chat frameworks do. The model API itself rejects a request that's too long. Losing the rules is an app design bug, avoided by sending them separately (Step 2).
- **"A schema stops hallucination."** A schema stops malformed answers; a well-formed answer can still be made up. Checking quotes against the source does that (Step 11).
- **Thresholds like 70 / 85 / 95%** are rules of thumb to tune per model, not standards.
- **Goal reminders and self-check loops cost tokens and time on every call.** They are trade-offs, not free fixes.

**What the chapter leaves out, which NurseOps Now needed:** workflow state with allowed transitions (Step 7), capping tool results (Step 3), caching (Step 8), and isolating memory per user and case (Step 1).

## Checklist: what is done and what is next

| Step | What | Status | Result |
|---|---|---|---|
| [1](#step-1-pick-and-load-the-thread) | Thread per user + case, survives restart | ✅ Done | 3 threads kept apart; 4 messages after restart |
| [2](#step-2-build-the-window) | Rules always sent; last 10 turns | 🟡 Partly | Turn limit works; no token count |
| [3](#step-3-load-facts-only-when-needed) | Facts by tool; results capped | ✅ Done | 12,000 characters, 4 rounds |
| [4](#step-4-hard-state-stays-in-sql) | Exact facts in SQL | ✅ Done | Never in chat |
| [5](#step-5-older-turns) | Older turns | 🟡 Partly | Kept on disk, not summarized |
| [6](#step-6-mask-then-save-the-turn) | Mask, then save | ✅ Done | DOB, phone, SSN masked |
| [7](#step-7-case-state-machine) | State machine + audit | ✅ Done | AI can't approve; 2 audit rows |
| [8](#step-8-reuse-instead-of-recompute) | Caching | 🟡 Partly | Review cached; Assist not prompt-cached |
| [9](#step-9-forget-on-request) | Forget | 🟡 Partly | Clear works; no expiry |
| [10](#step-10-gate-the-input-and-output) | Gates | ✅ Done | Prompt leak blocked |
| [11](#step-11-ground-every-answer) | Grounding | ✅ Done | Quote check with one retry |

## Findings: what the demos showed

All from the separate demo copy on Nov 19, 2026 (mock AI), plus the unit tests: **26 passed** in `test_assist.py`, `test_state.py` and `test_review_graph.py` (2.78 s).

- **Memory is isolated and durable.** Three threads stayed separate and survived a restart.
- **The window stays small.** After 12 turns, 24 messages were stored and 20 were sent.
- **Saved memory keeps no personal details.** Date of birth, phone and SSN were masked before saving.
- **The AI can't change a case's outcome.** Two non-human attempts to approve were refused; the human one worked, and both real moves were audited.
- **Six gaps, all named above:** no token count before calls; no summary of older turns; saved history grows without a limit; no automatic expiry; AI Assist not prompt-cached; no drift test over a long conversation. Also, the case review isn't checkpointed mid-run: a crash means the review reruns from the start (the case status only changes when it finishes, so nothing is left half-done).

## Plan: closing the gaps

1. **Count tokens before each call.** Use the API's token counting to check the window before sending, and drop or summarize more when it's near the limit.
_Plain example:_ checking your bag's weight before the airport, not at the gate.
_Done when:_ a 50-turn chat never exceeds a set budget, shown in the trace.
2. **Summarize older turns.** When turns fall out of the window, keep a short summary of what the nurse said (never case facts, which stay in SQL).
_Plain example:_ the meeting minutes, not the full recording.
_Done when:_ a fact said at turn 2 is still used correctly at turn 15.
3. **Cap and expire memory.** Keep at most N turns per thread on disk, and delete threads untouched for 90 days.
_Plain example:_ a mailbox that auto-archives old mail.
_Done when:_ a test shows old threads gone and an audit row for each.
4. **Prompt-cache AI Assist.** Mark the unchanged system prompt and tools as cacheable on Assist calls too.
_Plain example:_ keeping the handbook open instead of reopening it every question.
_Done when:_ traces show cache hits and lower cost per question.
5. **Test for drift.** A 50-turn scripted conversation that keeps trying to get an approval out of the AI.
_Plain example:_ a long, pushy customer call, rehearsed.
_Done when:_ the AI still refuses at turn 50, as part of the [eval plan](nurseops-now-evals.html).

## Tools

| Tool | What it does here | Status |
|---|---|---|
| LangGraph `SqliteSaver` | Saves each AI Assist thread after every step; reload by thread ID | In use |
| SQLite + SQLAlchemy | Cases, reviews, decisions, audit log, LLM cache | In use |
| Pydantic | Checks the shape of every AI review | In use |
| Anthropic SDK | System prompt field, prompt caching on reviews, token usage per call | In use |
| `app/pii.py` (regex) | Masks personal details in memory, logs and traces | In use |
| LangSmith | Traces each call, with a masked thread ID | In use |
| Token counting API | Window budget before each call | Will use |

## What this proves

NurseOps Now treats memory as a design decision, not a framework default. The rules are sent on every call so they can't be pushed out. Facts live as exact records and are looked up fresh, so they can't drift through summaries. Each nurse's conversation is a separate, masked, durable thread. And no conversation can change a case's outcome, because the state machine only lets a person approve. The gaps (token budget, summaries, expiry, caching for chat, a drift test) are named, with a plan for each.

All cases and people are synthetic. No real patient data is used.
