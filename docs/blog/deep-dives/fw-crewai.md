# Framework deep dive: CrewAI memory and the 27 solutions

Nov 19, 2026 · Michael Chang · Status: ⬜ not used in NurseOps Now (planned for restaurant-ai-platform, F14)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · Other frameworks: [LangGraph](fw-langgraph.html) · [AutoGen](fw-autogen.html) · [LlamaIndex](fw-llamaindex.html)

**Read in this order**

1. [In plain words](#in-plain-words)
2. [What it gives you for memory](#what-it-gives-you-for-memory): from the current docs
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): code and output
4. [The 27 solutions with CrewAI](#the-27-solutions-with-crewai): replace, complement or still yours
5. [Use both: what you still build](#use-both-what-you-still-build)
6. [In NurseOps Now](#in-nurseops-now), [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

CrewAI builds a "crew" of role-playing agents that work through tasks. Its memory is now one unified **`Memory`** class: agents `remember` facts and `recall` the relevant ones before each task, organized in **scopes** like folders (`/customer/acme`, `/agent/researcher`).

**In plain terms:** a shared team wiki with folders, which every teammate searches before starting a task.

## What it gives you for memory

From the official memory docs ([CrewAI memory docs](https://docs.crewai.com/en/concepts/memory)), checked on Nov 19, 2026:

- **One `Memory` class** replaces the old short-term, long-term, entity and external memory types.
- **Save and search:** `remember(content, scope=..., categories=..., importance=..., source=..., private=...)`, `recall(query, limit=..., scope=..., depth=...)`, `extract_memories(text)`.
- **Storage:** LanceDB in `./.crewai/memory` by default; `storage=` path or a `StorageBackend`; OpenAI embeddings by default (configurable `embedder`).
- **Ranking:** recency, semantic and importance weights; consolidation can merge or delete outdated records.
- **Deleting:** `memory.forget(scope=...)`, `memory.reset(scope=...)`, `crewai reset-memories`; no TTL.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: made-up data, no ServiceApps instance. The code is written from the current docs but not run (it needs an API key)._

**The scenario.** ServiceApps Assist's crew remembers facts per customer scope and recalls them before a task; one customer's memories are reset on request.

**Steps.**

1. Create `Memory()` (configure `embedder` and `storage` for production).
2. Save facts with a scope per customer or user, and `private=True` for sensitive ones.
3. Pass memory to the crew (`Crew(..., memory=memory)`) or give an agent a scoped view.
4. Delete one customer's memories with `memory.reset(scope=...)`.

**The code** (Python):

```python
from crewai import Agent, Crew, Memory, Task

memory = Memory(storage="./.crewai/memory")                     # LanceDB by default; set embedder= for production
memory.remember("Acme uses the corporate VPN profile v2", scope="/customer/acme", importance=0.8)
memory.remember("Acme's admin contact prefers email", scope="/customer/acme", private=True)

for m in memory.recall("how does acme connect to vpn", scope="/customer/acme", limit=3):
    print(round(m.score, 2), m.record.content)

assist = Agent(role="ServiceApps Assist", goal="Answer IT questions from KB articles",
               backstory="Cites KB numbers", memory=memory.scope("/customer/acme"))
crew = Crew(agents=[assist], tasks=[Task(description="Help Acme with VPN error 809",
                                         expected_output="Steps with KB citations", agent=assist)], memory=memory)

memory.reset(scope="/customer/acme")                           # forget one customer
```

**Output:** not run. CrewAI's memory sends content to an embedding model and an LLM (OpenAI by default) on every save, so it needs an API key. The code follows the current memory docs.

**What to watch for.**

- Memory content is sent to the configured LLM for analysis: use a local model for sensitive data, as the docs suggest.
- Consolidation can change or remove records automatically: never keep exact facts only here.
- Scope design is your per-user isolation and deletion plan; decide it before you store anything.
:::

## The 27 solutions with CrewAI

**🔁 Replace** = CrewAI does it, you configure it (9 of 27). **🤝 Complement** = use both: CrewAI gives the mechanism, you add the rules (8). **🛠 Still yours** = build it yourself (10). † = not a memory feature, so from general knowledge rather than the memory docs; check the current docs.

| Memory solution | With CrewAI | How | Solution |
|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | 🤝 Complement | Recalled memories are injected before each task; no chat-window setting on the memory page | [Deep dive](state-01-short-term-context-window.html) |
| **Three-Tier Memory: Long-Term (Vector Store)** | 🔁 Replace | Unified `Memory`: `remember` / `recall` with semantic search (LanceDB by default) | [Deep dive](state-02-long-term-vector-store.html) |
| **Three-Tier Memory: Episodic (Experience Log)** | 🤝 Complement | Memory records carry `source` and time; the audit log is yours | [Deep dive](state-03-episodic-experience-log.html) |
| **Agentic Outcome: Token Budgets** | 🛠 Still yours | Not on the memory page | [Deep dive](state-04-token-budgets.html) |
| **Agentic Outcome: Hybrid Memory Systems** | 🔁 Replace | One `Memory` recalled into every task | [Deep dive](state-05-hybrid-memory-systems.html) |
| **Agentic Outcome: Strict State Serialization** | 🤝 Complement | Memory is persistent; saving a run's state isn't on the memory page | [Deep dive](state-06-strict-state-serialization.html) |
| **Token Counting Middleware** | 🛠 Still yours | Not on the memory page | [Deep dive](state-07-token-counting-middleware.html) |
| **Dynamic Context Loading** | 🔁 Replace | Agent tools and knowledge sources are standard † | [Deep dive](state-08-dynamic-context-loading.html) |
| **System Prompt Pinning** | 🔁 Replace | Each agent's role, goal and backstory go into every task prompt † | [Deep dive](state-09-system-prompt-pinning.html) |
| **Textual Summarization** | 🤝 Complement | `extract_memories()` splits text into facts (not a summary) | [Deep dive](state-10-textual-summarization.html) |
| **Rolling Summaries** | 🛠 Still yours | Not built in | [Deep dive](state-11-rolling-summaries.html) |
| **Entity Extraction** | 🔁 Replace | `remember` analyzes content with an LLM (categories, importance); `extract_memories()` | [Deep dive](state-12-entity-extraction.html) |
| **Vector Compression via RAG** | 🔁 Replace | `recall(query)` over all saved memories | [Deep dive](state-13-vector-compression-via-rag.html) |
| **The Engineering Trade-off: Fidelity vs. Capacity** | 🛠 Still yours | Consolidation can merge or delete records automatically: keep exact facts elsewhere | [Deep dive](state-14-engineering-trade-off-fidelity-vs-capacity.html) |
| **The Hot/Cold State Architecture** | 🤝 Complement | The prompt is hot; `Memory` is cold | [Deep dive](state-15-hot-cold-state-architecture.html) |
| **Structured Storage (SQL/Postgres)** | 🛠 Still yours | Memory is stored in LanceDB, not your records | [Deep dive](state-16-structured-storage-sql-postgres.html) |
| **Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** | 🔁 Replace | LanceDB by default, or a custom `StorageBackend` | [Deep dive](state-17-semantic-storage-vector-db.html) |
| **Session Caching (Redis/Key-Value)** | 🛠 Still yours | No session or thread concept (scopes instead) | [Deep dive](state-18-session-caching-redis-key-value.html) |
| **The Rehydration Pattern** | 🔁 Replace | Relevant memories are recalled into each task, filtered by scope | [Deep dive](state-19-rehydration-pattern.html) |
| **Sanitization layer** | 🛠 Still yours | No redaction; `private` flag; docs suggest a local LLM for sensitive data | [Deep dive](state-20-sanitization-layer.html) |
| **TTL (time-to-live) expiration** | 🛠 Still yours | Not built in; `recency_half_life_days` only affects ranking | [Deep dive](state-21-ttl-expiration.html) |
| **GDPR Right to Be Forgotten** | 🤝 Complement | `memory.reset(scope="/customer/...")` clears one scope | [Deep dive](state-22-gdpr-right-to-be-forgotten.html) |
| **Engineering Fix: Recursive Goal Injection** | 🤝 Complement | Role and goal in every task prompt act as an anchor † | [Deep dive](state-23-recursive-goal-injection.html) |
| **Engineering Fix: Strict RAG and Citation Enforcement** | 🛠 Still yours | Yours † | [Deep dive](state-24-strict-rag-and-citation-enforcement.html) |
| **Input Filtering: Relevance Pruning** | 🛠 Still yours | Yours † | [Deep dive](state-25-input-filtering-relevance-pruning.html) |
| **Process Control: Self-Correction Loop** | 🤝 Complement | Task guardrails can reject output and retry † | [Deep dive](state-26-self-correction-loop.html) |
| **Output Guardrails: Schema Enforcement** | 🔁 Replace | Task `output_pydantic` / `output_json` † | [Deep dive](state-27-schema-enforcement.html) |

## Use both: what you still build

**Still yours with CrewAI:**

- **Agentic Outcome: Token Budgets**: Not on the memory page
- **Token Counting Middleware**: Not on the memory page
- **Rolling Summaries**: Not built in
- **The Engineering Trade-off: Fidelity vs. Capacity**: Consolidation can merge or delete records automatically: keep exact facts elsewhere
- **Structured Storage (SQL/Postgres)**: Memory is stored in LanceDB, not your records
- **Session Caching (Redis/Key-Value)**: No session or thread concept (scopes instead)
- **Sanitization layer**: No redaction; `private` flag; docs suggest a local LLM for sensitive data
- **TTL (time-to-live) expiration**: Not built in; `recency_half_life_days` only affects ranking
- **Engineering Fix: Strict RAG and Citation Enforcement**: Yours
- **Input Filtering: Relevance Pruning**: Yours

**Use both (complement), with your rules on top:**

- **Three-Tier Memory: Short-Term (Context Window)**: Recalled memories are injected before each task; no chat-window setting on the memory page
- **Three-Tier Memory: Episodic (Experience Log)**: Memory records carry `source` and time; the audit log is yours
- **Agentic Outcome: Strict State Serialization**: Memory is persistent; saving a run's state isn't on the memory page
- **Textual Summarization**: `extract_memories()` splits text into facts (not a summary)
- **The Hot/Cold State Architecture**: The prompt is hot; `Memory` is cold
- **GDPR Right to Be Forgotten**: `memory.reset(scope="/customer/...")` clears one scope
- **Engineering Fix: Recursive Goal Injection**: Role and goal in every task prompt act as an anchor
- **Process Control: Self-Correction Loop**: Task guardrails can reject output and retry

## In NurseOps Now

Not used in NurseOps Now. CrewAI is planned as feature F14 in restaurant-ai-platform.

## Trade-offs

- The least code for useful long-term memory, but the least control: LLM analysis and consolidation change what's stored.
- No conversation thread or token-window settings on the memory page; those are yours.

## Interview answer

"CrewAI gives me one Memory with scopes: agents remember and recall facts before each task, and I can reset one customer's scope for deletion. I'd keep exact facts in our own database, because CrewAI's LLM-based consolidation can rewrite memories, and I'd use a local model for anything sensitive."

All data in this post is made up.

[← Back to all 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
