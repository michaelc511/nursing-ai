# NurseOps Now: an AI copilot for prior authorization, feature by feature

Nov 10, 2026 · @Mitchy

## The problem: prior authorization is slow, and nurses carry it

NurseOps Now is a working prototype that aims to cut prior authorization turnaround by 40%, from 4.2 days to about 2.5, with no added headcount. The scenario is a regional health plan handling about 15,000 requests a month.

Nurses review every request by hand. Clinical documents arrive by fax, PDF, portal and provider upload. Today 22% of requests need rework because information is missing, and providers often call just to ask for a status.

The prototype uses synthetic data only, with no real patient information.

## What NurseOps Now is: AI reads and cites, people decide

NurseOps Now gives a nurse a prepared case instead of a stack of faxes. The AI does three jobs:

- **Intake and completeness.** It extracts the request details, flags missing documents up front and drafts the request to the provider. This targets the 22% rework.
- **Nurse copilot.** It compares the clinical documents with the coverage policy and returns a cited summary and a suggested tier: likely approve, needs review or likely deny.
- **Status visibility.** Every case has a status staff can look up, and AI Assist answers questions about cases, policies and rules.

The core rule is enforced in the service layer, not the screen: AI never approves or denies. A nurse can approve or pend. Only a medical director can deny. Every AI claim cites a page and a quote, and code checks each quote against the source PDF. A quote that can't be found sends the case to needs review.

Every decision is written to an audit trail with the AI output, the human decision, an override flag, the person and the time. Three imaging policies are in scope: lumbar spine MRI (CPT 72148), knee MRI (73721) and brain MRI (70551).

The architecture keeps one thick service layer. The React web app, the Typer CLI and the MCP server for Claude Cowork are thin clients over the same functions.

## How the AI fits together

Each case moves through a fixed path, so every AI step is visible and testable. The AI stops at a suggestion, and the status can only change to approved or denied through a person.

&#91;embedded content: NurseOps Now case flow, from intake to human decision\]

The missing-items path feeds straight back to intake, which is how the app targets the 22% rework.

## All 42 features, by area

The app was planned against a list of 42 AI engineering features. The plan includes 38 and skips 4 on purpose, and each row below can become its own post.

### Scope and foundation

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F0 App Idea and Scope Design | Written problem, goal, non-negotiables and success metrics before code | requirements, scope, success metrics |
| F1 Prototype Execution | CLI commands and a mock AI engine proved the flow before real AI calls | prototype, CLI, Typer |
| F4/S16 FastAPI Backend | Thin REST routes over the service layer | FastAPI, async, Pydantic, OpenAPI, uvicorn |
| F12 Engine Strategy Factory | Mock and Claude engines share one contract and swap by setting | strategy pattern, factory, interface |
| F12.1 Parallel Entry Point | A frozen linear baseline sits next to the LangGraph flow for comparison | baseline, strangler pattern, safe rollout |

### Ingestion and indexing

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F3 Semantic RAG and Vector Store | Policies only are embedded and searched; patient documents are never put in RAG | RAG, Chroma, sentence-transformers, embeddings, top-k |
| S14 Clause-Aware Chunking | Each chunk is one policy clause with a header naming its policy, version, section and page | semantic chunking, contextual headers |
| S4 Metadata Extraction | CPT code, policy number, version, section and page make chunks filterable and traceable | metadata, filtering, lineage |
| N1 Document Parsing | OCR reads image-only PDFs such as scanned faxes | OCR, layout parsing, scanned PDFs |
| N2 Incremental Re-index and Versioning | Policies are versioned and re-embedded when added or updated | incremental indexing, versioning |

### Retrieval quality

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F18/S9 Hybrid Search | Keyword and vector results are fused, so exact terms and meaning both count | BM25, dense + sparse, Reciprocal Rank Fusion |
| F10/S10 Cross-Encoder Re-ranking | A second stage reads question and clause together and picks the best | two-stage retrieval, cross-encoder, precision@k |
| S8 Query Rewriting | Casual questions are rewritten into the policy's own language before search | query rewriting, query expansion, pre-retrieval |

### Prompting and generation

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F3.1 System Prompt and Persona | Versioned prompt files define the rules: cite, never decide, say "I don't know" | system prompt, grounding, citations, structured output |
| F2 Dynamic LLM Selector | Staff can switch between Claude models in demo mode | model selection, provider abstraction, Claude |
| N3 Cache and Model Fallback | Repeat calls can be cached and a fallback model takes over; if Claude is down the case goes to needs review | caching, failover, graceful degradation |

### Agents and tools

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F13/S17 LangGraph Engines | The case review runs as an explicit graph of steps | LangGraph, StateGraph, nodes, edges |
| F13.1 LangGraph State Machine | Reading the CPT code comes before policy lookup and the full review, on a fixed path | state machine, deterministic flow |
| F13.2 Agentic RAG | AI Assist chooses among read-only tools for cases, policies and the user guide, with a capped number of rounds | agent, tool calling, agentic RAG |
| F8 FastMCP Server | Seven tools let Claude Cowork run intake and reviews; there is deliberately no decision tool | MCP, FastMCP, Streamable HTTP, bearer token |
| F11 Text-to-SQL | Not used: agent tools call the service layer instead of writing SQL | text-to-SQL, least privilege |
| F14 CrewAI | Not used: optional, LangGraph covers the need | CrewAI, multi-agent |
| F15 AutoGen | Not used: optional, LangGraph covers the need | AutoGen, multi-agent |

### Memory

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F7 Chat Memory | AI Assist remembers recent turns per user and case | conversation memory, context window |
| F16 Persistent Checkpointing | Chat state survives restarts in a SQLite checkpoint store | LangGraph checkpointer, SqliteSaver |

### Safety, security and privacy

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F22 Prompt-Injection Defense | Document text is treated as data; instruction-like text raises a warning and forces needs review | prompt injection, guardrails, untrusted input |
| F19 Intent Gating | Off-topic questions are blocked before they reach the model | intent classification, topic guardrails |
| S5 PII Sanitization | Personal data is redacted from logs, traces and chat history | PII redaction, HIPAA-minded design |
| F21/S21 Auth, Rate Limiting and RBAC | Role rules live in services, with per-user AI limits and a daily cost cap | RBAC, rate limiting, cost cap |
| N5 Red Teaming | 44 generated attacks check for leaks, false decisions and status changes | red teaming, adversarial testing |

### Evaluation and QA

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F17 RAG Evals Harness | A golden set scores retrieval, reviews, AI Assist and safety, with an LLM judge and RAGAS | evals, golden set, hit@k, LLM judge, RAGAS, faithfulness |
| F20 CI Eval Gate | The build fails if a score drops more than 0.05 or a safety case fails | CI, regression gate, GitHub Actions |
| F23 Unit Tests | Fully mocked backend and frontend suites | pytest, vitest, mocking, coverage |

### Observability and cost

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F9 Tracing | Each AI run records step timings, tokens and cost, without content | tracing, LangSmith, observability |
| F6 Token and Cost Accounting | Calls, tokens, cost and latency are tracked overall and per case | token usage, cost tracking, latency |
| N4 Online Quality Monitoring | Thumbs, override rate and unverified quote rate feed quality alerts | online evals, feedback loop, drift alerts |

### Interfaces and deployment

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| F5 Web Interfaces | React queue, case detail with citations, decision form and AI Assist chat | React, Vite, TypeScript |
| F24 Deploy | Docker on Fly.io, planned next | Docker, Fly.io, deployment |
| N8 Production Ops and Compliance | Production runbooks and compliance work, planned next | SLOs, runbooks, HIPAA, BAA |

### Governance, process and emerging

| Feature | How NurseOps Now uses it | Keywords |
| --- | --- | --- |
| N6 AI Governance | Human-in-the-loop rules and audit trail are in place; governance documents come next | AI governance, audit trail, human in the loop |
| F25 Retro and Memory | Each build phase is tracked, with session logs and retros | retrospective, build log |
| N7 GraphRAG / Multimodal | Not used: optional, a watch-list item | GraphRAG, multimodal |

## Where it stands today

NurseOps Now runs end to end on a local machine, and testing on real Claude has started. It is not deployed yet.

| Status | Features |
| --- | --- |
| Built and tested with mocks | 23 |
| Built, being proven on real Claude | 13 |
| Planned next (deployment and production ops) | 2 |
| Skipped on purpose | 4 |

Real Claude has reviewed sample cases and answered through AI Assist's tools, and every citation in those reviews checked out against its source. Live evaluation scored 1.0 on reviews and safety and 0.875 on AI Assist, and the red team ran 44 attacks with none getting through.

Since then the app has been deployed to Fly.io (https://nurseops-now.fly.dev), governance documents were written, and on 2026-11-14 Claude Cowork was connected over MCP: a scheduled task now takes in new requests, has Claude review them and reports what needs people, without making any decision.

## Ideas for deep-dive posts

- **Human in the loop:** why AI never denies, service-layer enforcement, audit trail, override rate
- **Citations you can trust:** page-and-quote citations, code-checked quotes, structured output, Pydantic
- **Policy RAG:** clause-aware chunking, Chroma, hybrid search, Reciprocal Rank Fusion, cross-encoder re-ranking, query rewriting
- **Agents with limits:** LangGraph, state machines, agentic RAG, read-only tools, memory, checkpointing
- **MCP as a thin adapter:** FastMCP, Streamable HTTP, Claude Cowork, no decision tool
- **Safety for healthcare AI:** prompt injection, intent gating, PII redaction, red teaming, HIPAA-minded design
- **Proving it works:** golden sets, LLM judges, RAGAS, CI eval gates
- **Running it for real:** tracing, cost accounting, rate limits, model fallback, Fly.io
