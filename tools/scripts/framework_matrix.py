"""How LangGraph, AutoGen, CrewAI and LlamaIndex cover the 27 state-management solutions (Chapter 7, intro + 7.1-7.4).

Verdicts: R = 🔁 Replace (the framework does it; you configure it), C = 🤝 Complement (use both: the framework gives
the mechanism, you add the rules), Y = 🛠 Still yours (build it yourself).
Memory rows were checked against each framework's official memory docs on 2026-11-19 (DOCS below). Rows outside
memory (tools, prompts, guardrails, structured output) are from general knowledge: marked in NOTE_GENERAL.
"""

FW = ["LangGraph", "AutoGen", "CrewAI", "LlamaIndex"]
ICON = {"R": "🔁 Replace", "C": "🤝 Complement", "Y": "🛠 Still yours"}
DOCS = {
    "LangGraph": "https://docs.langchain.com/oss/python/langgraph/memory",
    "AutoGen": "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html",
    "CrewAI": "https://docs.crewai.com/en/concepts/memory",
    "LlamaIndex": "https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/",
}
NOTE_GENERAL = {"Dynamic Context Loading", "System Prompt Pinning", "Engineering Fix: Recursive Goal Injection",
                "Engineering Fix: Strict RAG and Citation Enforcement", "Input Filtering: Relevance Pruning",
                "Process Control: Self-Correction Loop", "Output Guardrails: Schema Enforcement"}

# title -> {framework: (verdict, note)}, plus "overall"
M = {
"Three-Tier Memory: Short-Term (Context Window)": dict(
    LangGraph=("C", "Messages live in graph state per thread; you trim them with `trim_messages`"),
    AutoGen=("R", "The agent's model context: `BufferedChatCompletionContext`, `TokenLimitedChatCompletionContext`, `HeadAndTailChatCompletionContext`"),
    CrewAI=("C", "Recalled memories are injected before each task; no chat-window setting on the memory page"),
    LlamaIndex=("R", "`Memory.from_defaults(session_id=..., token_limit=...)` manages the chat history"),
    overall="🔁 / 🤝"),
"Three-Tier Memory: Long-Term (Vector Store)": dict(
    LangGraph=("R", "Store (`InMemoryStore`, `PostgresStore`, …) with semantic search, per namespace"),
    AutoGen=("R", "`ChromaDBVectorMemory`, `RedisMemory`, `Mem0Memory`"),
    CrewAI=("R", "Unified `Memory`: `remember` / `recall` with semantic search (LanceDB by default)"),
    LlamaIndex=("R", "`VectorMemoryBlock` on any vector store"),
    overall="🔁 Replace (for agent memory)"),
"Three-Tier Memory: Episodic (Experience Log)": dict(
    LangGraph=("C", "`get_state_history` replays a thread's checkpoints; the audit log is yours"),
    AutoGen=("C", "`ListMemory` keeps a chronological list; the audit log is yours"),
    CrewAI=("C", "Memory records carry `source` and time; the audit log is yours"),
    LlamaIndex=("C", "The chat store keeps messages per session; the audit log is yours"),
    overall="🤝 Complement"),
"Agentic Outcome: Token Budgets": dict(
    LangGraph=("C", "`trim_messages(max_tokens=...)`; the budget per zone is yours"),
    AutoGen=("R", "`TokenLimitedChatCompletionContext(token_limit=...)` (experimental)"),
    CrewAI=("Y", "Not on the memory page"),
    LlamaIndex=("R", "`token_limit`, `chat_history_token_ratio` and block `priority` decide what's kept"),
    overall="🤝 Complement"),
"Agentic Outcome: Hybrid Memory Systems": dict(
    LangGraph=("R", "Checkpointer (short-term) + Store (long-term) in one graph"),
    AutoGen=("R", "Model context + `memory=[...]` on the agent"),
    CrewAI=("R", "One `Memory` recalled into every task"),
    LlamaIndex=("R", "Short-term chat + memory blocks in one `Memory`"),
    overall="🔁 Replace"),
"Agentic Outcome: Strict State Serialization": dict(
    LangGraph=("R", "Checkpointers save after every step; resume with `invoke(None, config)`; `durability` modes"),
    AutoGen=("C", "`save_state()` / `load_state()` return a dict; storing it is yours"),
    CrewAI=("C", "Memory is persistent; saving a run's state isn't on the memory page"),
    LlamaIndex=("C", "Workflow `ctx.to_dict()` / `Context.from_dict()`; Memory is stored separately"),
    overall="🔁 LangGraph, 🤝 others"),
"Token Counting Middleware": dict(
    LangGraph=("C", "`trim_messages` with a `token_counter`; thresholds and actions are yours"),
    AutoGen=("R", "`TokenLimitedChatCompletionContext` counts with `model_client.count_tokens()`"),
    CrewAI=("Y", "Not on the memory page"),
    LlamaIndex=("R", "Counts tokens (tiktoken by default) and flushes old messages past the limit"),
    overall="🤝 Complement"),
"Dynamic Context Loading": dict(
    LangGraph=("R", "Tools and tool nodes are standard"),
    AutoGen=("R", "Tools on `AssistantAgent` are standard"),
    CrewAI=("R", "Agent tools and knowledge sources are standard"),
    LlamaIndex=("R", "Tools and query engines are standard"),
    overall="🔁 Replace"),
"System Prompt Pinning": dict(
    LangGraph=("C", "You add the system prompt in your node, outside the trimmed history"),
    AutoGen=("C", "`HeadAndTailChatCompletionContext` can always keep the first messages"),
    CrewAI=("R", "Each agent's role, goal and backstory go into every task prompt"),
    LlamaIndex=("R", "`StaticMemoryBlock` with `priority=0` is always inserted, never truncated"),
    overall="🔁 / 🤝"),
"Textual Summarization": dict(
    LangGraph=("C", "LangMem `SummarizationNode`, or a custom `summary` key"),
    AutoGen=("Y", "Not built in"),
    CrewAI=("C", "`extract_memories()` splits text into facts (not a summary)"),
    LlamaIndex=("Y", "The summary buffer is deprecated; old messages are flushed to memory blocks instead"),
    overall="🛠 Mostly yours"),
"Rolling Summaries": dict(
    LangGraph=("C", "LangMem `SummarizationNode(max_tokens_before_summary=...)`"),
    AutoGen=("Y", "Not built in"),
    CrewAI=("Y", "Not built in"),
    LlamaIndex=("C", "Past `chat_history_token_ratio`, the oldest messages move to long-term blocks"),
    overall="🤝 / 🛠"),
"Entity Extraction": dict(
    LangGraph=("C", "Write extracted facts to the Store yourself, or use LangMem"),
    AutoGen=("C", "`Mem0Memory` extracts facts (an outside service)"),
    CrewAI=("R", "`remember` analyzes content with an LLM (categories, importance); `extract_memories()`"),
    LlamaIndex=("R", "`FactExtractionMemoryBlock(max_facts=...)`"),
    overall="🔁 CrewAI and LlamaIndex, 🤝 others"),
"Vector Compression via RAG": dict(
    LangGraph=("R", "Store semantic search over saved memories"),
    AutoGen=("R", "ChromaDB or Redis vector memory"),
    CrewAI=("R", "`recall(query)` over all saved memories"),
    LlamaIndex=("R", "Flushed messages go into a `VectorMemoryBlock`"),
    overall="🔁 Replace"),
"The Engineering Trade-off: Fidelity vs. Capacity": dict(
    LangGraph=("Y", "No hard/soft split; your exact facts belong in your own tables"),
    AutoGen=("Y", "Same"),
    CrewAI=("Y", "Consolidation can merge or delete records automatically: keep exact facts elsewhere"),
    LlamaIndex=("Y", "Fact extraction is an LLM rewrite: keep exact facts elsewhere"),
    overall="🛠 Still yours"),
"The Hot/Cold State Architecture": dict(
    LangGraph=("C", "Graph state is hot; checkpointers and the Store are cold; you decide what goes where"),
    AutoGen=("C", "Model context is hot; `Memory` and saved state are cold"),
    CrewAI=("C", "The prompt is hot; `Memory` is cold"),
    LlamaIndex=("C", "Short-term chat is hot; memory blocks are cold"),
    overall="🤝 Complement"),
"Structured Storage (SQL/Postgres)": dict(
    LangGraph=("Y", "`PostgresSaver` stores checkpoints, not your business tables"),
    AutoGen=("Y", "None"),
    CrewAI=("Y", "Memory is stored in LanceDB, not your records"),
    LlamaIndex=("Y", "A SQL chat store holds messages, not your records"),
    overall="🛠 Still yours"),
"Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)": dict(
    LangGraph=("R", "Store with an `index` (embeddings), many backends"),
    AutoGen=("R", "`ChromaDBVectorMemory`, `RedisMemory`"),
    CrewAI=("R", "LanceDB by default, or a custom `StorageBackend`"),
    LlamaIndex=("R", "`VectorMemoryBlock` on any LlamaIndex vector store"),
    overall="🔁 for agent memory, 🤝 for documents with permissions"),
"Session Caching (Redis/Key-Value)": dict(
    LangGraph=("R", "Checkpointers incl. `RedisSaver`, keyed by `thread_id`"),
    AutoGen=("C", "`save_state()` gives a dict; you store it under your session key"),
    CrewAI=("Y", "No session or thread concept (scopes instead)"),
    LlamaIndex=("R", "`session_id` with a SQL chat store (`async_database_uri`)"),
    overall="🔁 LangGraph and LlamaIndex"),
"The Rehydration Pattern": dict(
    LangGraph=("C", "Reload by `thread_id`, memories by namespace; filtering and injection are yours"),
    AutoGen=("C", "`load_state()`; memory adds relevant items to the context"),
    CrewAI=("R", "Relevant memories are recalled into each task, filtered by scope"),
    LlamaIndex=("R", "`memory.get()` returns recent chat plus memory blocks"),
    overall="🤝 Complement"),
"Sanitization layer": dict(
    LangGraph=("Y", "No redaction; `EncryptedSerializer` encrypts checkpoints at rest"),
    AutoGen=("Y", "No redaction"),
    CrewAI=("Y", "No redaction; `private` flag; docs suggest a local LLM for sensitive data"),
    LlamaIndex=("Y", "Not on the memory page"),
    overall="🛠 Still yours"),
"TTL (time-to-live) expiration": dict(
    LangGraph=("Y", "No built-in TTL in the docs; they suggest a cron job to delete old checkpoints"),
    AutoGen=("Y", "Not mentioned"),
    CrewAI=("Y", "Not built in; `recency_half_life_days` only affects ranking"),
    LlamaIndex=("Y", "Not mentioned"),
    overall="🛠 Still yours"),
"GDPR Right to Be Forgotten": dict(
    LangGraph=("C", "`checkpointer.delete_thread(thread_id)`; Store items deleted by key"),
    AutoGen=("C", "`memory.clear()` clears a whole store, not one user"),
    CrewAI=("C", "`memory.reset(scope=\"/customer/...\")` clears one scope"),
    LlamaIndex=("C", "Delete messages in the chat store by session"),
    overall="🤝 Complement (covering every store is yours)"),
"Engineering Fix: Recursive Goal Injection": dict(
    LangGraph=("C", "Add the reminder in the node that builds the prompt"),
    AutoGen=("Y", "Yours to add"),
    CrewAI=("C", "Role and goal in every task prompt act as an anchor"),
    LlamaIndex=("C", "A `StaticMemoryBlock` reminder is inserted every turn"),
    overall="🤝 Complement"),
"Engineering Fix: Strict RAG and Citation Enforcement": dict(
    LangGraph=("Y", "Retrieval tools yes; checking citations is yours"),
    AutoGen=("Y", "Yours"),
    CrewAI=("Y", "Yours"),
    LlamaIndex=("C", "Citation-style query engines return numbered sources; checking them is yours"),
    overall="🛠 Still yours"),
"Input Filtering: Relevance Pruning": dict(
    LangGraph=("C", "Add a gate node before the model (as NurseOps Now does)"),
    AutoGen=("Y", "Yours"),
    CrewAI=("Y", "Yours"),
    LlamaIndex=("Y", "Yours"),
    overall="🛠 Still yours"),
"Process Control: Self-Correction Loop": dict(
    LangGraph=("C", "Conditional edges loop back to the model; the check is yours"),
    AutoGen=("C", "A second agent can review (reflection pattern)"),
    CrewAI=("C", "Task guardrails can reject output and retry"),
    LlamaIndex=("C", "Workflows can loop back; the check is yours"),
    overall="🤝 Complement"),
"Output Guardrails: Schema Enforcement": dict(
    LangGraph=("R", "Structured output with a Pydantic model"),
    AutoGen=("R", "Structured output on `AssistantAgent`"),
    CrewAI=("R", "Task `output_pydantic` / `output_json`"),
    LlamaIndex=("R", "Structured output with a Pydantic `output_cls`"),
    overall="🔁 Replace"),
}

SECTION_OF = {  # parent section key for each title, in the book's order
    "intro": ["Three-Tier Memory: Short-Term (Context Window)", "Three-Tier Memory: Long-Term (Vector Store)",
              "Three-Tier Memory: Episodic (Experience Log)", "Agentic Outcome: Token Budgets",
              "Agentic Outcome: Hybrid Memory Systems", "Agentic Outcome: Strict State Serialization"],
    "71": ["Token Counting Middleware", "Dynamic Context Loading", "System Prompt Pinning"],
    "72": ["Textual Summarization", "Rolling Summaries", "Entity Extraction", "Vector Compression via RAG",
           "The Engineering Trade-off: Fidelity vs. Capacity"],
    "73": ["The Hot/Cold State Architecture", "Structured Storage (SQL/Postgres)",
           "Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)", "Session Caching (Redis/Key-Value)",
           "The Rehydration Pattern", "Sanitization layer", "TTL (time-to-live) expiration", "GDPR Right to Be Forgotten"],
    "74": ["Engineering Fix: Recursive Goal Injection", "Engineering Fix: Strict RAG and Citation Enforcement",
           "Input Filtering: Relevance Pruning", "Process Control: Self-Correction Loop",
           "Output Guardrails: Schema Enforcement"],
}
assert sum(len(v) for v in SECTION_OF.values()) == len(M) == 27
