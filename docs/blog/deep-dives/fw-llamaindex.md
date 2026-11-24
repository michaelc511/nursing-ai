# Framework deep dive: LlamaIndex memory and the 27 solutions

Nov 19, 2026 · Michael Chang · Status: ⬜ not used in NurseOps Now

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · Other frameworks: [LangGraph](fw-langgraph.html) · [AutoGen](fw-autogen.html) · [CrewAI](fw-crewai.html)

**Read in this order**

1. [In plain words](#in-plain-words)
2. [What it gives you for memory](#what-it-gives-you-for-memory): from the current docs
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): code and output
4. [The 27 solutions with LlamaIndex](#the-27-solutions-with-llamaindex): replace, complement or still yours
5. [Use both: what you still build](#use-both-what-you-still-build)
6. [In NurseOps Now](#in-nurseops-now), [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

LlamaIndex is best known for RAG over documents, and its agents get a **`Memory`** object per session: recent chat is kept up to a token limit, and older messages are flushed into long-term **memory blocks** (static text, extracted facts, or a vector store).

**In plain terms:** a notepad with a size limit; when it's full, the oldest notes are filed into labeled binders, and one sticky note (the rules) is always on top.

## What it gives you for memory

From the official memory docs ([LlamaIndex memory docs](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/)), checked on Nov 19, 2026:

- **Short-term:** `Memory.from_defaults(session_id=..., token_limit=...)`; past `chat_history_token_ratio`, the oldest messages are flushed (`token_flush_size`); tiktoken counts tokens by default.
- **Long-term blocks:** `StaticMemoryBlock` (always inserted), `FactExtractionMemoryBlock(max_facts=...)`, `VectorMemoryBlock(vector_store, embed_model, similarity_top_k)`; `priority` decides what's truncated first (0 = never).
- **Persistence:** an in-memory SQLite chat store by default; a remote SQL database via `async_database_uri`; workflow state with `ctx.to_dict()` / `Context.from_dict()`.
- **Older classes** (`ChatMemoryBuffer`, `ChatSummaryMemoryBuffer`, `VectorMemory`) are deprecated in favor of `Memory`.
- **Deleting:** chat-store level (delete messages by session); no TTL.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: made-up data, no ServiceApps instance. The code was run as shown; the model is a scripted stand-in, so no API key is needed._

**The scenario.** ServiceApps Assist with a 60-token memory and a pinned rules block: after seven messages, only the newest chat still fits next to the rules.

**Steps.**

1. Create `Memory.from_defaults(session_id=..., token_limit=...)` per conversation.
2. Add a `StaticMemoryBlock` with `priority=0` for the rules (never truncated).
3. Add a `FactExtractionMemoryBlock` or `VectorMemoryBlock` to keep what gets flushed.
4. Point it at a real database (`async_database_uri`) in production.

**The code** (Python):

```python
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import Memory, StaticMemoryBlock

rules = StaticMemoryBlock(name="rules", static_content="You are ServiceApps Assist. Cite KB numbers.", priority=0)
memory = Memory.from_defaults(session_id="u42:INC0012345", token_limit=60,         # short-term limit (7.1)
                              chat_history_token_ratio=0.5, token_flush_size=20,
                              memory_blocks=[rules])                                # pinned rules (7.1)
turns = [("user", "My VPN keeps dropping on my laptop at the hotel"), ("assistant", "Which error code do you see?"),
         ("user", "Error 809 every time I connect"), ("assistant", "809 means the VPN can't reach the server."),
         ("user", "I'm on the hotel guest Wi-Fi right now"), ("assistant", "Avoid guest Wi-Fi; try your phone hotspot."),
         ("user", "Still failing on the hotspot too")]
for role, text in turns:
    memory.put(ChatMessage(role=role, content=text))
sent = memory.get()                                    # what the next model call receives
print("stored messages :", len(memory.get_all()))
print("sent next call  :", len(sent), "messages")
print("first one sent  :", sent[0].role.value, "->", str(sent[0].content)[:90])
print("oldest chat sent:", [m.content for m in sent if m.role.value == "user"][0])
```

**Output** (from running the code above on Nov 19, 2026):

```
stored messages : 7
sent next call  : 4 messages
first one sent  : system -> <memory>
<rules>
You are ServiceApps Assist. Cite KB numbers.
</rules>
</memory>
oldest chat sent: I'm on the hotel guest Wi-Fi right now
```

**What to watch for.**

- Without a fact or vector block, flushed messages simply leave the window.
- The default store is in memory: configure a database for anything that must survive a restart.
- No redaction or TTL: mask before `put()` and clean up by session.
:::

## The 27 solutions with LlamaIndex

**🔁 Replace** = LlamaIndex does it, you configure it (13 of 27). **🤝 Complement** = use both: LlamaIndex gives the mechanism, you add the rules (8). **🛠 Still yours** = build it yourself (6). † = not a memory feature, so from general knowledge rather than the memory docs; check the current docs.

| Memory solution | With LlamaIndex | How | Solution |
|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | 🔁 Replace | `Memory.from_defaults(session_id=..., token_limit=...)` manages the chat history | [Deep dive](state-01-short-term-context-window.html) |
| **Three-Tier Memory: Long-Term (Vector Store)** | 🔁 Replace | `VectorMemoryBlock` on any vector store | [Deep dive](state-02-long-term-vector-store.html) |
| **Three-Tier Memory: Episodic (Experience Log)** | 🤝 Complement | The chat store keeps messages per session; the audit log is yours | [Deep dive](state-03-episodic-experience-log.html) |
| **Agentic Outcome: Token Budgets** | 🔁 Replace | `token_limit`, `chat_history_token_ratio` and block `priority` decide what's kept | [Deep dive](state-04-token-budgets.html) |
| **Agentic Outcome: Hybrid Memory Systems** | 🔁 Replace | Short-term chat + memory blocks in one `Memory` | [Deep dive](state-05-hybrid-memory-systems.html) |
| **Agentic Outcome: Strict State Serialization** | 🤝 Complement | Workflow `ctx.to_dict()` / `Context.from_dict()`; Memory is stored separately | [Deep dive](state-06-strict-state-serialization.html) |
| **Token Counting Middleware** | 🔁 Replace | Counts tokens (tiktoken by default) and flushes old messages past the limit | [Deep dive](state-07-token-counting-middleware.html) |
| **Dynamic Context Loading** | 🔁 Replace | Tools and query engines are standard † | [Deep dive](state-08-dynamic-context-loading.html) |
| **System Prompt Pinning** | 🔁 Replace | `StaticMemoryBlock` with `priority=0` is always inserted, never truncated † | [Deep dive](state-09-system-prompt-pinning.html) |
| **Textual Summarization** | 🛠 Still yours | The summary buffer is deprecated; old messages are flushed to memory blocks instead | [Deep dive](state-10-textual-summarization.html) |
| **Rolling Summaries** | 🤝 Complement | Past `chat_history_token_ratio`, the oldest messages move to long-term blocks | [Deep dive](state-11-rolling-summaries.html) |
| **Entity Extraction** | 🔁 Replace | `FactExtractionMemoryBlock(max_facts=...)` | [Deep dive](state-12-entity-extraction.html) |
| **Vector Compression via RAG** | 🔁 Replace | Flushed messages go into a `VectorMemoryBlock` | [Deep dive](state-13-vector-compression-via-rag.html) |
| **The Engineering Trade-off: Fidelity vs. Capacity** | 🛠 Still yours | Fact extraction is an LLM rewrite: keep exact facts elsewhere | [Deep dive](state-14-engineering-trade-off-fidelity-vs-capacity.html) |
| **The Hot/Cold State Architecture** | 🤝 Complement | Short-term chat is hot; memory blocks are cold | [Deep dive](state-15-hot-cold-state-architecture.html) |
| **Structured Storage (SQL/Postgres)** | 🛠 Still yours | A SQL chat store holds messages, not your records | [Deep dive](state-16-structured-storage-sql-postgres.html) |
| **Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** | 🔁 Replace | `VectorMemoryBlock` on any LlamaIndex vector store | [Deep dive](state-17-semantic-storage-vector-db.html) |
| **Session Caching (Redis/Key-Value)** | 🔁 Replace | `session_id` with a SQL chat store (`async_database_uri`) | [Deep dive](state-18-session-caching-redis-key-value.html) |
| **The Rehydration Pattern** | 🔁 Replace | `memory.get()` returns recent chat plus memory blocks | [Deep dive](state-19-rehydration-pattern.html) |
| **Sanitization layer** | 🛠 Still yours | Not on the memory page | [Deep dive](state-20-sanitization-layer.html) |
| **TTL (time-to-live) expiration** | 🛠 Still yours | Not mentioned | [Deep dive](state-21-ttl-expiration.html) |
| **GDPR Right to Be Forgotten** | 🤝 Complement | Delete messages in the chat store by session | [Deep dive](state-22-gdpr-right-to-be-forgotten.html) |
| **Engineering Fix: Recursive Goal Injection** | 🤝 Complement | A `StaticMemoryBlock` reminder is inserted every turn † | [Deep dive](state-23-recursive-goal-injection.html) |
| **Engineering Fix: Strict RAG and Citation Enforcement** | 🤝 Complement | Citation-style query engines return numbered sources; checking them is yours † | [Deep dive](state-24-strict-rag-and-citation-enforcement.html) |
| **Input Filtering: Relevance Pruning** | 🛠 Still yours | Yours † | [Deep dive](state-25-input-filtering-relevance-pruning.html) |
| **Process Control: Self-Correction Loop** | 🤝 Complement | Workflows can loop back; the check is yours † | [Deep dive](state-26-self-correction-loop.html) |
| **Output Guardrails: Schema Enforcement** | 🔁 Replace | Structured output with a Pydantic `output_cls` † | [Deep dive](state-27-schema-enforcement.html) |

## Use both: what you still build

**Still yours with LlamaIndex:**

- **Textual Summarization**: The summary buffer is deprecated; old messages are flushed to memory blocks instead
- **The Engineering Trade-off: Fidelity vs. Capacity**: Fact extraction is an LLM rewrite: keep exact facts elsewhere
- **Structured Storage (SQL/Postgres)**: A SQL chat store holds messages, not your records
- **Sanitization layer**: Not on the memory page
- **TTL (time-to-live) expiration**: Not mentioned
- **Input Filtering: Relevance Pruning**: Yours

**Use both (complement), with your rules on top:**

- **Three-Tier Memory: Episodic (Experience Log)**: The chat store keeps messages per session; the audit log is yours
- **Agentic Outcome: Strict State Serialization**: Workflow `ctx.to_dict()` / `Context.from_dict()`; Memory is stored separately
- **Rolling Summaries**: Past `chat_history_token_ratio`, the oldest messages move to long-term blocks
- **The Hot/Cold State Architecture**: Short-term chat is hot; memory blocks are cold
- **GDPR Right to Be Forgotten**: Delete messages in the chat store by session
- **Engineering Fix: Recursive Goal Injection**: A `StaticMemoryBlock` reminder is inserted every turn
- **Engineering Fix: Strict RAG and Citation Enforcement**: Citation-style query engines return numbered sources; checking them is yours
- **Process Control: Self-Correction Loop**: Workflows can loop back; the check is yours

## In NurseOps Now

Not used in NurseOps Now; its RAG is built directly on Chroma and sentence-transformers.

## Trade-offs

- The best built-in token window plus long-term blocks, and strong RAG, but persistence and deletion are lower-level.
- Fact extraction is an LLM rewrite: useful, but not a record of truth.

## Interview answer

"In LlamaIndex I'd use Memory per session with a token limit, a static block with the rules at priority zero so they're never cut, and a fact or vector block to catch what overflows. It's the best built-in window management of the four; persistence and deletion I'd wire to our own database."

All data in this post is made up.

[← Back to all 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
