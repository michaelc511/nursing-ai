# Framework deep dive: AutoGen memory and the 27 solutions

Nov 19, 2026 · Michael Chang · Status: ⬜ not used in NurseOps Now (planned for restaurant-ai-platform, F15)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · Other frameworks: [LangGraph](fw-langgraph.html) · [CrewAI](fw-crewai.html) · [LlamaIndex](fw-llamaindex.html)

**Read in this order**

1. [In plain words](#in-plain-words)
2. [What it gives you for memory](#what-it-gives-you-for-memory): from the current docs
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): code and output
4. [The 27 solutions with AutoGen](#the-27-solutions-with-autogen): replace, complement or still yours
5. [Use both: what you still build](#use-both-what-you-still-build)
6. [In NurseOps Now](#in-nurseops-now), [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

AutoGen (Microsoft) builds apps from agents that talk to each other. Each agent has a **model context** (what it sends to the model, with ready-made limits), optional **memory** stores it consults before answering, and **save/load state** to pause and resume.

**In plain terms:** each agent has a short notepad with a fixed number of lines, an optional reference binder, and can photocopy its notepad to continue later.

## What it gives you for memory

From the official memory docs ([AutoGen memory docs](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html)), checked on Nov 19, 2026:

- **Short-term:** `BufferedChatCompletionContext(buffer_size=N)`, `TokenLimitedChatCompletionContext(model_client, token_limit=...)` (experimental), `HeadAndTailChatCompletionContext(head_size, tail_size)`, `UnboundedChatCompletionContext`.
- **Persistence:** `await agent.save_state()` / `load_state(state)`, also for teams; the state is a dict you store yourself.
- **Long-term:** the `Memory` protocol (`add`, `query`, `update_context`, `clear`) with `ListMemory`, `ChromaDBVectorMemory`, `RedisMemory`, `Mem0Memory`.
- **Deleting:** `memory.clear()` (the whole store), `model_context.clear()`, `team.reset()`; no TTL or per-user delete in the docs.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: made-up data, no ServiceApps instance. The code was run as shown; the model is a scripted stand-in, so no API key is needed._

**The scenario.** ServiceApps Assist as one AutoGen agent with a 4-message buffer and a small preference memory. The model is AutoGen's replay client (scripted replies), so the example runs without an API key.

**Steps.**

1. Give the agent a model context with a limit (`BufferedChatCompletionContext`).
2. Attach long-term memory (`memory=[ListMemory()]` or a vector memory).
3. After each turn, `save_state()` and store the JSON under your session key.
4. To resume, create the agent and `load_state()`; to forget, `clear()` the memory and delete the saved state.

**The code** (Python):

```python
import asyncio, json
from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.replay import ReplayChatCompletionClient

async def main():
    replies = ["Which error code do you see?", "809: the VPN can't reach the server. Avoid guest Wi-Fi.", "Try your phone hotspot."]
    prefs = ListMemory()                                                          # long-term memory (7.3)
    await prefs.add(MemoryContent(content="User prefers short bullet answers", mime_type=MemoryMimeType.TEXT))
    agent = AssistantAgent("assist", model_client=ReplayChatCompletionClient(replies),
                           system_message="You are ServiceApps Assist. Cite KB numbers.",
                           model_context=BufferedChatCompletionContext(buffer_size=4),   # short-term limit (7.1)
                           memory=[prefs])
    for q in ["My VPN keeps dropping", "Error 809", "I'm on hotel Wi-Fi"]:
        r = await agent.run(task=q)
        print(f"{q!r:24} -> {r.messages[-1].content}")
    kept = await agent._model_context.get_messages()                              # what the next call would see
    print("model context keeps:", len(kept), "messages (buffer_size=4)")
    state = await agent.save_state()                                              # serialization (7.3)
    blob = json.dumps(state)
    print("saved state:", len(blob), "chars of JSON, keys:", sorted(state))
    agent2 = AssistantAgent("assist", model_client=ReplayChatCompletionClient(["(resumed)"]),
                            model_context=BufferedChatCompletionContext(buffer_size=4))
    await agent2.load_state(json.loads(blob))
    print("restored context:", len(await agent2._model_context.get_messages()), "messages")
    await prefs.clear()
    print("memory after clear():", (await prefs.query("anything")).results)

asyncio.run(main())
```

**Output** (from running the code above on Nov 19, 2026):

```
'My VPN keeps dropping'  -> Which error code do you see?
'Error 809'              -> 809: the VPN can't reach the server. Avoid guest Wi-Fi.
"I'm on hotel Wi-Fi"     -> Try your phone hotspot.
model context keeps: 4 messages (buffer_size=4)
saved state: 1055 chars of JSON, keys: ['llm_context', 'type', 'version']
restored context: 4 messages
memory after clear(): []
```

**What to watch for.**

- `save_state()` gives you a dict; where it's stored, under which key, and for how long is your job.
- `memory.clear()` clears everything in that store; keep one store per user if you need per-user deletion.
- No redaction: mask before `memory.add()`.
:::

## The 27 solutions with AutoGen

**🔁 Replace** = AutoGen does it, you configure it (9 of 27). **🤝 Complement** = use both: AutoGen gives the mechanism, you add the rules (9). **🛠 Still yours** = build it yourself (9). † = not a memory feature, so from general knowledge rather than the memory docs; check the current docs.

| Book solution | With AutoGen | How | Solution |
|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | 🔁 Replace | The agent's model context: `BufferedChatCompletionContext`, `TokenLimitedChatCompletionContext`, `HeadAndTailChatCompletionContext` | [Deep dive](state-01-short-term-context-window.html) |
| **Three-Tier Memory: Long-Term (Vector Store)** | 🔁 Replace | `ChromaDBVectorMemory`, `RedisMemory`, `Mem0Memory` | [Deep dive](state-02-long-term-vector-store.html) |
| **Three-Tier Memory: Episodic (Experience Log)** | 🤝 Complement | `ListMemory` keeps a chronological list; the audit log is yours | [Deep dive](state-03-episodic-experience-log.html) |
| **Agentic Outcome: Token Budgets** | 🔁 Replace | `TokenLimitedChatCompletionContext(token_limit=...)` (experimental) | [Deep dive](state-04-token-budgets.html) |
| **Agentic Outcome: Hybrid Memory Systems** | 🔁 Replace | Model context + `memory=[...]` on the agent | [Deep dive](state-05-hybrid-memory-systems.html) |
| **Agentic Outcome: Strict State Serialization** | 🤝 Complement | `save_state()` / `load_state()` return a dict; storing it is yours | [Deep dive](state-06-strict-state-serialization.html) |
| **Token Counting Middleware** | 🔁 Replace | `TokenLimitedChatCompletionContext` counts with `model_client.count_tokens()` | [Deep dive](state-07-token-counting-middleware.html) |
| **Dynamic Context Loading** | 🔁 Replace | Tools on `AssistantAgent` are standard † | [Deep dive](state-08-dynamic-context-loading.html) |
| **System Prompt Pinning** | 🤝 Complement | `HeadAndTailChatCompletionContext` can always keep the first messages † | [Deep dive](state-09-system-prompt-pinning.html) |
| **Textual Summarization** | 🛠 Still yours | Not built in | [Deep dive](state-10-textual-summarization.html) |
| **Rolling Summaries** | 🛠 Still yours | Not built in | [Deep dive](state-11-rolling-summaries.html) |
| **Entity Extraction** | 🤝 Complement | `Mem0Memory` extracts facts (an outside service) | [Deep dive](state-12-entity-extraction.html) |
| **Vector Compression via RAG** | 🔁 Replace | ChromaDB or Redis vector memory | [Deep dive](state-13-vector-compression-via-rag.html) |
| **The Engineering Trade-off: Fidelity vs. Capacity** | 🛠 Still yours | Same | [Deep dive](state-14-engineering-trade-off-fidelity-vs-capacity.html) |
| **The Hot/Cold State Architecture** | 🤝 Complement | Model context is hot; `Memory` and saved state are cold | [Deep dive](state-15-hot-cold-state-architecture.html) |
| **Structured Storage (SQL/Postgres)** | 🛠 Still yours | None | [Deep dive](state-16-structured-storage-sql-postgres.html) |
| **Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** | 🔁 Replace | `ChromaDBVectorMemory`, `RedisMemory` | [Deep dive](state-17-semantic-storage-vector-db.html) |
| **Session Caching (Redis/Key-Value)** | 🤝 Complement | `save_state()` gives a dict; you store it under your session key | [Deep dive](state-18-session-caching-redis-key-value.html) |
| **The Rehydration Pattern** | 🤝 Complement | `load_state()`; memory adds relevant items to the context | [Deep dive](state-19-rehydration-pattern.html) |
| **Sanitization layer** | 🛠 Still yours | No redaction | [Deep dive](state-20-sanitization-layer.html) |
| **TTL (time-to-live) expiration** | 🛠 Still yours | Not mentioned | [Deep dive](state-21-ttl-expiration.html) |
| **GDPR Right to Be Forgotten** | 🤝 Complement | `memory.clear()` clears a whole store, not one user | [Deep dive](state-22-gdpr-right-to-be-forgotten.html) |
| **Engineering Fix: Recursive Goal Injection** | 🛠 Still yours | Yours to add † | [Deep dive](state-23-recursive-goal-injection.html) |
| **Engineering Fix: Strict RAG and Citation Enforcement** | 🛠 Still yours | Yours † | [Deep dive](state-24-strict-rag-and-citation-enforcement.html) |
| **Input Filtering: Relevance Pruning** | 🛠 Still yours | Yours † | [Deep dive](state-25-input-filtering-relevance-pruning.html) |
| **Process Control: Self-Correction Loop** | 🤝 Complement | A second agent can review (reflection pattern) † | [Deep dive](state-26-self-correction-loop.html) |
| **Output Guardrails: Schema Enforcement** | 🔁 Replace | Structured output on `AssistantAgent` † | [Deep dive](state-27-schema-enforcement.html) |

## Use both: what you still build

**Still yours with AutoGen:**

- **Textual Summarization**: Not built in
- **Rolling Summaries**: Not built in
- **The Engineering Trade-off: Fidelity vs. Capacity**: Same
- **Structured Storage (SQL/Postgres)**: None
- **Sanitization layer**: No redaction
- **TTL (time-to-live) expiration**: Not mentioned
- **Engineering Fix: Recursive Goal Injection**: Yours to add
- **Engineering Fix: Strict RAG and Citation Enforcement**: Yours
- **Input Filtering: Relevance Pruning**: Yours

**Use both (complement), with your rules on top:**

- **Three-Tier Memory: Episodic (Experience Log)**: `ListMemory` keeps a chronological list; the audit log is yours
- **Agentic Outcome: Strict State Serialization**: `save_state()` / `load_state()` return a dict; storing it is yours
- **System Prompt Pinning**: `HeadAndTailChatCompletionContext` can always keep the first messages
- **Entity Extraction**: `Mem0Memory` extracts facts (an outside service)
- **The Hot/Cold State Architecture**: Model context is hot; `Memory` and saved state are cold
- **Session Caching (Redis/Key-Value)**: `save_state()` gives a dict; you store it under your session key
- **The Rehydration Pattern**: `load_state()`; memory adds relevant items to the context
- **GDPR Right to Be Forgotten**: `memory.clear()` clears a whole store, not one user
- **Process Control: Self-Correction Loop**: A second agent can review (reflection pattern)

## In NurseOps Now

Not used in NurseOps Now. AutoGen is planned as feature F15 in restaurant-ai-platform.

## Trade-offs

- Ready-made window limits (including a token limit), but persistence is a dict you manage.
- Multi-agent conversations multiply memory: each agent has its own context.

## Interview answer

"In AutoGen I'd give each agent a bounded model context, buffered or token-limited, attach vector memory for long-term facts, and save_state after each turn to my own store under a session key. Clearing and retention are mine to design, because memory.clear() wipes a whole store."

All data in this post is made up.

[← Back to all 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
