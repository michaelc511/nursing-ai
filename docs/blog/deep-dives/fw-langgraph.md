# Framework deep dive: LangGraph memory and the 27 solutions

Nov 19, 2026 · Michael Chang · Status: ✅ used in NurseOps Now (AI Assist)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · Other frameworks: [AutoGen](fw-autogen.html) · [CrewAI](fw-crewai.html) · [LlamaIndex](fw-llamaindex.html)

**Read in this order**

1. [In plain words](#in-plain-words)
2. [What it gives you for memory](#what-it-gives-you-for-memory): from the current docs
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): code and output
4. [The 27 solutions with LangGraph](#the-27-solutions-with-langgraph): replace, complement or still yours
5. [Use both: what you still build](#use-both-what-you-still-build)
6. [In NurseOps Now](#in-nurseops-now), [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

LangGraph builds an AI app as a graph of steps (nodes) that share a state. Its memory story is two pieces: a **checkpointer** that saves each conversation (thread) after every step, and a **Store** for long-term memories shared across conversations.

**In plain terms:** a notebook per conversation that saves itself after every line, plus a shared filing cabinet per user.

## What it gives you for memory

From the official memory docs ([LangGraph memory docs](https://docs.langchain.com/oss/python/langgraph/memory)), checked on Nov 19, 2026:

- **Short-term:** messages in graph state, saved per `thread_id`; trim with `trim_messages` (by tokens) or delete with `RemoveMessage`.
- **Persistence:** checkpointers `InMemorySaver`, `SqliteSaver`, `PostgresSaver`, `MongoDBSaver`, `RedisSaver` (and more); `get_state`, `get_state_history`, resume with `invoke(None, config)`; `durability` modes; `EncryptedSerializer` for encryption at rest.
- **Long-term:** Store (`InMemoryStore`, `PostgresStore`, `RedisStore`, …) with tuple namespaces like `(user_id, "memories")`, `put` / `get` / `search`, optional semantic search with an `index`.
- **Summarizing:** LangMem's `SummarizationNode`, or your own `summary` key.
- **Deleting:** `checkpointer.delete_thread(thread_id)`; no built-in TTL (the docs suggest a cron job).

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: made-up data, no ServiceApps instance. The code was run as shown; the model is a scripted stand-in, so no API key is needed._

**The scenario.** ServiceApps Assist as a one-node graph: each conversation is a thread (`u42:INC0012345`), the user's saved preference is in the Store, and only the last ~60 tokens of chat are sent.

**Steps.**

1. Compile the graph with a checkpointer (persistence) and a Store (long-term memory).
2. Pass `thread_id` (conversation) and `user_id` in the config on every call.
3. In the node, trim the messages by tokens and read the user's memories from the Store.
4. Delete a conversation with `checkpointer.delete_thread()`.

**The code** (Python):

```python
from langchain_core.messages import AIMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

RULES = "You are ServiceApps Assist. Cite KB numbers."

def respond(state: MessagesState, config, *, store: BaseStore):
    user = config["configurable"]["user_id"]
    window = trim_messages(state["messages"], strategy="last", token_counter=count_tokens_approximately,
                           max_tokens=60, start_on="human")                 # short-term limit (7.1)
    prefs = [i.value["text"] for i in store.search((user, "memories"))]   # long-term memory (7.3)
    # a real node would call the model with RULES + prefs + window; here we report what it would send
    return {"messages": [AIMessage(f"(would send {len(window)} of {len(state['messages'])} messages; memories: {prefs})")]}

builder = StateGraph(MessagesState)
builder.add_node("respond", respond)
builder.add_edge(START, "respond")
store = InMemoryStore()
graph = builder.compile(checkpointer=InMemorySaver(), store=store)            # persistence + long-term store

store.put(("u42", "memories"), "pref-1", {"text": "prefers short bullet answers"})
cfg = {"configurable": {"thread_id": "u42:INC0012345", "user_id": "u42"}}
for q in ["My VPN shows error 809", "I'm on hotel Wi-Fi", "Still failing on my hotspot"]:
    out = graph.invoke({"messages": [HumanMessage(q)]}, cfg)
    print(f"{q!r:32} -> {out['messages'][-1].content}")

print("saved in thread:", len(graph.get_state(cfg).values["messages"]), "messages")
new = {"configurable": {"thread_id": "u42:general", "user_id": "u42"}}
print("new thread, same user:", graph.invoke({"messages": [HumanMessage("Hi")]}, new)["messages"][-1].content)
graph.checkpointer.delete_thread("u42:INC0012345")
print("after delete_thread:", graph.get_state(cfg).values.get("messages", []))
```

**Output** (from running the code above on Nov 19, 2026):

```
'My VPN shows error 809'         -> (would send 1 of 1 messages; memories: ['prefers short bullet answers'])
"I'm on hotel Wi-Fi"             -> (would send 3 of 3 messages; memories: ['prefers short bullet answers'])
'Still failing on my hotspot'    -> (would send 3 of 5 messages; memories: ['prefers short bullet answers'])
saved in thread: 6 messages
new thread, same user: (would send 1 of 1 messages; memories: ['prefers short bullet answers'])
after delete_thread: []
```

**What to watch for.**

- Use `SqliteSaver` / `PostgresSaver` in production; `InMemorySaver` loses everything on restart.
- Mask personal data before it reaches state or the Store; LangGraph doesn't redact.
- Plan retention yourself: delete old threads on a schedule.
:::

## The 27 solutions with LangGraph

**🔁 Replace** = LangGraph does it, you configure it (8 of 27). **🤝 Complement** = use both: LangGraph gives the mechanism, you add the rules (14). **🛠 Still yours** = build it yourself (5). † = not a memory feature, so from general knowledge rather than the memory docs; check the current docs.

| Memory solution | With LangGraph | How | Solution |
|---|---|---|---|
| **Three-Tier Memory: Short-Term (Context Window)** | 🤝 Complement | Messages live in graph state per thread; you trim them with `trim_messages` | [Deep dive](state-01-short-term-context-window.html) |
| **Three-Tier Memory: Long-Term (Vector Store)** | 🔁 Replace | Store (`InMemoryStore`, `PostgresStore`, …) with semantic search, per namespace | [Deep dive](state-02-long-term-vector-store.html) |
| **Three-Tier Memory: Episodic (Experience Log)** | 🤝 Complement | `get_state_history` replays a thread's checkpoints; the audit log is yours | [Deep dive](state-03-episodic-experience-log.html) |
| **Agentic Outcome: Token Budgets** | 🤝 Complement | `trim_messages(max_tokens=...)`; the budget per zone is yours | [Deep dive](state-04-token-budgets.html) |
| **Agentic Outcome: Hybrid Memory Systems** | 🔁 Replace | Checkpointer (short-term) + Store (long-term) in one graph | [Deep dive](state-05-hybrid-memory-systems.html) |
| **Agentic Outcome: Strict State Serialization** | 🔁 Replace | Checkpointers save after every step; resume with `invoke(None, config)`; `durability` modes | [Deep dive](state-06-strict-state-serialization.html) |
| **Token Counting Middleware** | 🤝 Complement | `trim_messages` with a `token_counter`; thresholds and actions are yours | [Deep dive](state-07-token-counting-middleware.html) |
| **Dynamic Context Loading** | 🔁 Replace | Tools and tool nodes are standard † | [Deep dive](state-08-dynamic-context-loading.html) |
| **System Prompt Pinning** | 🤝 Complement | You add the system prompt in your node, outside the trimmed history † | [Deep dive](state-09-system-prompt-pinning.html) |
| **Textual Summarization** | 🤝 Complement | LangMem `SummarizationNode`, or a custom `summary` key | [Deep dive](state-10-textual-summarization.html) |
| **Rolling Summaries** | 🤝 Complement | LangMem `SummarizationNode(max_tokens_before_summary=...)` | [Deep dive](state-11-rolling-summaries.html) |
| **Entity Extraction** | 🤝 Complement | Write extracted facts to the Store yourself, or use LangMem | [Deep dive](state-12-entity-extraction.html) |
| **Vector Compression via RAG** | 🔁 Replace | Store semantic search over saved memories | [Deep dive](state-13-vector-compression-via-rag.html) |
| **The Engineering Trade-off: Fidelity vs. Capacity** | 🛠 Still yours | No hard/soft split; your exact facts belong in your own tables | [Deep dive](state-14-engineering-trade-off-fidelity-vs-capacity.html) |
| **The Hot/Cold State Architecture** | 🤝 Complement | Graph state is hot; checkpointers and the Store are cold; you decide what goes where | [Deep dive](state-15-hot-cold-state-architecture.html) |
| **Structured Storage (SQL/Postgres)** | 🛠 Still yours | `PostgresSaver` stores checkpoints, not your business tables | [Deep dive](state-16-structured-storage-sql-postgres.html) |
| **Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)** | 🔁 Replace | Store with an `index` (embeddings), many backends | [Deep dive](state-17-semantic-storage-vector-db.html) |
| **Session Caching (Redis/Key-Value)** | 🔁 Replace | Checkpointers incl. `RedisSaver`, keyed by `thread_id` | [Deep dive](state-18-session-caching-redis-key-value.html) |
| **The Rehydration Pattern** | 🤝 Complement | Reload by `thread_id`, memories by namespace; filtering and injection are yours | [Deep dive](state-19-rehydration-pattern.html) |
| **Sanitization layer** | 🛠 Still yours | No redaction; `EncryptedSerializer` encrypts checkpoints at rest | [Deep dive](state-20-sanitization-layer.html) |
| **TTL (time-to-live) expiration** | 🛠 Still yours | No built-in TTL in the docs; they suggest a cron job to delete old checkpoints | [Deep dive](state-21-ttl-expiration.html) |
| **GDPR Right to Be Forgotten** | 🤝 Complement | `checkpointer.delete_thread(thread_id)`; Store items deleted by key | [Deep dive](state-22-gdpr-right-to-be-forgotten.html) |
| **Engineering Fix: Recursive Goal Injection** | 🤝 Complement | Add the reminder in the node that builds the prompt † | [Deep dive](state-23-recursive-goal-injection.html) |
| **Engineering Fix: Strict RAG and Citation Enforcement** | 🛠 Still yours | Retrieval tools yes; checking citations is yours † | [Deep dive](state-24-strict-rag-and-citation-enforcement.html) |
| **Input Filtering: Relevance Pruning** | 🤝 Complement | Add a gate node before the model (as NurseOps Now does) † | [Deep dive](state-25-input-filtering-relevance-pruning.html) |
| **Process Control: Self-Correction Loop** | 🤝 Complement | Conditional edges loop back to the model; the check is yours † | [Deep dive](state-26-self-correction-loop.html) |
| **Output Guardrails: Schema Enforcement** | 🔁 Replace | Structured output with a Pydantic model † | [Deep dive](state-27-schema-enforcement.html) |

## Use both: what you still build

**Still yours with LangGraph:**

- **The Engineering Trade-off: Fidelity vs. Capacity**: No hard/soft split; your exact facts belong in your own tables
- **Structured Storage (SQL/Postgres)**: `PostgresSaver` stores checkpoints, not your business tables
- **Sanitization layer**: No redaction; `EncryptedSerializer` encrypts checkpoints at rest
- **TTL (time-to-live) expiration**: No built-in TTL in the docs; they suggest a cron job to delete old checkpoints
- **Engineering Fix: Strict RAG and Citation Enforcement**: Retrieval tools yes; checking citations is yours

**Use both (complement), with your rules on top:**

- **Three-Tier Memory: Short-Term (Context Window)**: Messages live in graph state per thread; you trim them with `trim_messages`
- **Three-Tier Memory: Episodic (Experience Log)**: `get_state_history` replays a thread's checkpoints; the audit log is yours
- **Agentic Outcome: Token Budgets**: `trim_messages(max_tokens=...)`; the budget per zone is yours
- **Token Counting Middleware**: `trim_messages` with a `token_counter`; thresholds and actions are yours
- **System Prompt Pinning**: You add the system prompt in your node, outside the trimmed history
- **Textual Summarization**: LangMem `SummarizationNode`, or a custom `summary` key
- **Rolling Summaries**: LangMem `SummarizationNode(max_tokens_before_summary=...)`
- **Entity Extraction**: Write extracted facts to the Store yourself, or use LangMem
- **The Hot/Cold State Architecture**: Graph state is hot; checkpointers and the Store are cold; you decide what goes where
- **The Rehydration Pattern**: Reload by `thread_id`, memories by namespace; filtering and injection are yours
- **GDPR Right to Be Forgotten**: `checkpointer.delete_thread(thread_id)`; Store items deleted by key
- **Engineering Fix: Recursive Goal Injection**: Add the reminder in the node that builds the prompt
- **Input Filtering: Relevance Pruning**: Add a gate node before the model (as NurseOps Now does)
- **Process Control: Self-Correction Loop**: Conditional edges loop back to the model; the check is yours

## In NurseOps Now

Used today: AI Assist compiles its LangGraph graph with `SqliteSaver` (`backend/app/services/assist.py`), one thread per user and case, cleared with `delete_thread()`. Masking (`pii.py`), the 10-turn window and SQL facts are NurseOps' own. The next step would be the Store for long-term per-user memory.

## Trade-offs

- Most control and the best persistence story, but you write more of the flow yourself.
- Short-term limits and summaries are your code (or LangMem), not automatic.

## Interview answer

"In LangGraph I use a checkpointer for per-thread memory, which saves after every step so a conversation survives restarts, and the Store for long-term memories by user namespace. I trim by tokens in the node, mask before saving, and delete threads on a schedule because there's no built-in TTL."

All data in this post is made up.

[← Back to all 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
