"""Build the 4 agent-framework memory deep dives and the per-section framework tables in the state blog.

- docs/blog/deep-dives/fw-<name>.md (+ .html): LangGraph, AutoGen, CrewAI, LlamaIndex memory, mapped to the 27 book
  solutions (framework_matrix.py), with a ServiceApps example. LangGraph code runs in backend/venv; AutoGen and
  LlamaIndex code run in a separate env given by FW_PYTHON (pip install autogen-agentchat autogen-ext llama-index-core);
  CrewAI code is illustrative (its memory needs an embedder + LLM API key). Example code: tools/scripts/fw_examples/.
- docs/blog/nurseops-now-state.md: a "With LangGraph, AutoGen, CrewAI and LlamaIndex (<section>)" table after each
  section's solutions (inserted or replaced in place).

Usage (repo root):  FW_PYTHON=/path/to/env/bin/python python3 tools/scripts/make_framework_deep_dives.py
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BLOG = ROOT / "docs" / "blog"
OUT = BLOG / "deep-dives"
PARENT = BLOG / "nurseops-now-state.md"
KIT = pathlib.Path("/Users/mike/projects/claude-config/blog-format/kit/build_blog.py")
VENV = ROOT / "backend" / "venv" / "bin" / "python"
FW_PY = os.environ.get("FW_PYTHON")
DATE = "Nov 19, 2026"
sys.path.insert(0, str(HERE))
from framework_matrix import DOCS, FW, ICON, M, NOTE_GENERAL, SECTION_OF  # noqa: E402
from state_solutions import SECTIONS, SOLUTIONS  # noqa: E402

SLUG = {s["title"]: f"state-{i:02d}-{s['slug']}" for i, s in enumerate(SOLUTIONS, 1)}
FILE = {f: f"fw-{f.lower()}" for f in FW}
TAG = {"intro": "Intro", "71": "7.1", "72": "7.2", "73": "7.3", "74": "7.4"}

FWINFO = {
"LangGraph": dict(
 runs="venv", status="✅ used in NurseOps Now (AI Assist)",
 plain="LangGraph builds an AI app as a graph of steps (nodes) that share a state. Its memory story is two pieces: a **checkpointer** that saves each conversation (thread) after every step, and a **Store** for long-term memories shared across conversations.",
 plain_terms="a notebook per conversation that saves itself after every line, plus a shared filing cabinet per user.",
 gives=["**Short-term:** messages in graph state, saved per `thread_id`; trim with `trim_messages` (by tokens) or delete with `RemoveMessage`.",
        "**Persistence:** checkpointers `InMemorySaver`, `SqliteSaver`, `PostgresSaver`, `MongoDBSaver`, `RedisSaver` (and more); `get_state`, `get_state_history`, resume with `invoke(None, config)`; `durability` modes; `EncryptedSerializer` for encryption at rest.",
        "**Long-term:** Store (`InMemoryStore`, `PostgresStore`, `RedisStore`, …) with tuple namespaces like `(user_id, \"memories\")`, `put` / `get` / `search`, optional semantic search with an `index`.",
        "**Summarizing:** LangMem's `SummarizationNode`, or your own `summary` key.",
        "**Deleting:** `checkpointer.delete_thread(thread_id)`; no built-in TTL (the docs suggest a cron job)."],
 scenario="ServiceApps Assist as a one-node graph: each conversation is a thread (`u42:INC0012345`), the user's saved preference is in the Store, and only the last ~60 tokens of chat are sent.",
 steps=["Compile the graph with a checkpointer (persistence) and a Store (long-term memory).",
        "Pass `thread_id` (conversation) and `user_id` in the config on every call.",
        "In the node, trim the messages by tokens and read the user's memories from the Store.",
        "Delete a conversation with `checkpointer.delete_thread()`."],
 code="",
 watch=["Use `SqliteSaver` / `PostgresSaver` in production; `InMemorySaver` loses everything on restart.",
        "Mask personal data before it reaches state or the Store; LangGraph doesn't redact.",
        "Plan retention yourself: delete old threads on a schedule."],
 nurseops="Used today: AI Assist compiles its LangGraph graph with `SqliteSaver` (`backend/app/services/assist.py`), one thread per user and case, cleared with `delete_thread()`. Masking (`pii.py`), the 10-turn window and SQL facts are NurseOps' own. The next step would be the Store for long-term per-user memory.",
 tradeoffs=["Most control and the best persistence story, but you write more of the flow yourself.",
            "Short-term limits and summaries are your code (or LangMem), not automatic."],
 interview="In LangGraph I use a checkpointer for per-thread memory, which saves after every step so a conversation survives restarts, and the Store for long-term memories by user namespace. I trim by tokens in the node, mask before saving, and delete threads on a schedule because there's no built-in TTL."),
"AutoGen": dict(
 runs="fw", status="⬜ not used in NurseOps Now (planned for restaurant-ai-platform, F15)",
 plain="AutoGen (Microsoft) builds apps from agents that talk to each other. Each agent has a **model context** (what it sends to the model, with ready-made limits), optional **memory** stores it consults before answering, and **save/load state** to pause and resume.",
 plain_terms="each agent has a short notepad with a fixed number of lines, an optional reference binder, and can photocopy its notepad to continue later.",
 gives=["**Short-term:** `BufferedChatCompletionContext(buffer_size=N)`, `TokenLimitedChatCompletionContext(model_client, token_limit=...)` (experimental), `HeadAndTailChatCompletionContext(head_size, tail_size)`, `UnboundedChatCompletionContext`.",
        "**Persistence:** `await agent.save_state()` / `load_state(state)`, also for teams; the state is a dict you store yourself.",
        "**Long-term:** the `Memory` protocol (`add`, `query`, `update_context`, `clear`) with `ListMemory`, `ChromaDBVectorMemory`, `RedisMemory`, `Mem0Memory`.",
        "**Deleting:** `memory.clear()` (the whole store), `model_context.clear()`, `team.reset()`; no TTL or per-user delete in the docs."],
 scenario="ServiceApps Assist as one AutoGen agent with a 4-message buffer and a small preference memory. The model is AutoGen's replay client (scripted replies), so the example runs without an API key.",
 steps=["Give the agent a model context with a limit (`BufferedChatCompletionContext`).",
        "Attach long-term memory (`memory=[ListMemory()]` or a vector memory).",
        "After each turn, `save_state()` and store the JSON under your session key.",
        "To resume, create the agent and `load_state()`; to forget, `clear()` the memory and delete the saved state."],
 code="", watch=["`save_state()` gives you a dict; where it's stored, under which key, and for how long is your job.",
        "`memory.clear()` clears everything in that store; keep one store per user if you need per-user deletion.",
        "No redaction: mask before `memory.add()`."],
 nurseops="Not used in NurseOps Now. AutoGen is planned as feature F15 in restaurant-ai-platform.",
 tradeoffs=["Ready-made window limits (including a token limit), but persistence is a dict you manage.",
            "Multi-agent conversations multiply memory: each agent has its own context."],
 interview="In AutoGen I'd give each agent a bounded model context, buffered or token-limited, attach vector memory for long-term facts, and save_state after each turn to my own store under a session key. Clearing and retention are mine to design, because memory.clear() wipes a whole store."),
"CrewAI": dict(
 runs="no", status="⬜ not used in NurseOps Now (planned for restaurant-ai-platform, F14)",
 plain="CrewAI builds a \"crew\" of role-playing agents that work through tasks. Its memory is now one unified **`Memory`** class: agents `remember` facts and `recall` the relevant ones before each task, organized in **scopes** like folders (`/customer/acme`, `/agent/researcher`).",
 plain_terms="a shared team wiki with folders, which every teammate searches before starting a task.",
 gives=["**One `Memory` class** replaces the old short-term, long-term, entity and external memory types.",
        "**Save and search:** `remember(content, scope=..., categories=..., importance=..., source=..., private=...)`, `recall(query, limit=..., scope=..., depth=...)`, `extract_memories(text)`.",
        "**Storage:** LanceDB in `./.crewai/memory` by default; `storage=` path or a `StorageBackend`; OpenAI embeddings by default (configurable `embedder`).",
        "**Ranking:** recency, semantic and importance weights; consolidation can merge or delete outdated records.",
        "**Deleting:** `memory.forget(scope=...)`, `memory.reset(scope=...)`, `crewai reset-memories`; no TTL."],
 scenario="ServiceApps Assist's crew remembers facts per customer scope and recalls them before a task; one customer's memories are reset on request.",
 steps=["Create `Memory()` (configure `embedder` and `storage` for production).",
        "Save facts with a scope per customer or user, and `private=True` for sensitive ones.",
        "Pass memory to the crew (`Crew(..., memory=memory)`) or give an agent a scoped view.",
        "Delete one customer's memories with `memory.reset(scope=...)`."],
 code="", watch=["Memory content is sent to the configured LLM for analysis: use a local model for sensitive data, as the docs suggest.",
        "Consolidation can change or remove records automatically: never keep exact facts only here.",
        "Scope design is your per-user isolation and deletion plan; decide it before you store anything."],
 nurseops="Not used in NurseOps Now. CrewAI is planned as feature F14 in restaurant-ai-platform.",
 tradeoffs=["The least code for useful long-term memory, but the least control: LLM analysis and consolidation change what's stored.",
            "No conversation thread or token-window settings on the memory page; those are yours."],
 interview="CrewAI gives me one Memory with scopes: agents remember and recall facts before each task, and I can reset one customer's scope for deletion. I'd keep exact facts in our own database, because CrewAI's LLM-based consolidation can rewrite memories, and I'd use a local model for anything sensitive."),
"LlamaIndex": dict(
 runs="fw", status="⬜ not used in NurseOps Now",
 plain="LlamaIndex is best known for RAG over documents, and its agents get a **`Memory`** object per session: recent chat is kept up to a token limit, and older messages are flushed into long-term **memory blocks** (static text, extracted facts, or a vector store).",
 plain_terms="a notepad with a size limit; when it's full, the oldest notes are filed into labeled binders, and one sticky note (the rules) is always on top.",
 gives=["**Short-term:** `Memory.from_defaults(session_id=..., token_limit=...)`; past `chat_history_token_ratio`, the oldest messages are flushed (`token_flush_size`); tiktoken counts tokens by default.",
        "**Long-term blocks:** `StaticMemoryBlock` (always inserted), `FactExtractionMemoryBlock(max_facts=...)`, `VectorMemoryBlock(vector_store, embed_model, similarity_top_k)`; `priority` decides what's truncated first (0 = never).",
        "**Persistence:** an in-memory SQLite chat store by default; a remote SQL database via `async_database_uri`; workflow state with `ctx.to_dict()` / `Context.from_dict()`.",
        "**Older classes** (`ChatMemoryBuffer`, `ChatSummaryMemoryBuffer`, `VectorMemory`) are deprecated in favor of `Memory`.",
        "**Deleting:** chat-store level (delete messages by session); no TTL."],
 scenario="ServiceApps Assist with a 60-token memory and a pinned rules block: after seven messages, only the newest chat still fits next to the rules.",
 steps=["Create `Memory.from_defaults(session_id=..., token_limit=...)` per conversation.",
        "Add a `StaticMemoryBlock` with `priority=0` for the rules (never truncated).",
        "Add a `FactExtractionMemoryBlock` or `VectorMemoryBlock` to keep what gets flushed.",
        "Point it at a real database (`async_database_uri`) in production."],
 code="", watch=["Without a fact or vector block, flushed messages simply leave the window.",
        "The default store is in memory: configure a database for anything that must survive a restart.",
        "No redaction or TTL: mask before `put()` and clean up by session."],
 nurseops="Not used in NurseOps Now; its RAG is built directly on Chroma and sentence-transformers.",
 tradeoffs=["The best built-in token window plus long-term blocks, and strong RAG, but persistence and deletion are lower-level.",
            "Fact extraction is an LLM rewrite: useful, but not a record of truth."],
 interview="In LlamaIndex I'd use Memory per session with a token limit, a static block with the rules at priority zero so they're never cut, and a fact or vector block to catch what overflows. It's the best built-in window management of the four; persistence and deletion I'd wire to our own database."),
}

CODE = {
"LangGraph": None,  # filled from the tested scratch example below
"AutoGen": None, "LlamaIndex": None,
"CrewAI": '''from crewai import Agent, Crew, Memory, Task

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
''',
}


def run(py, code):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "ex.py"
        f.write_text(code)
        r = subprocess.run([str(py), "-I", str(f)], capture_output=True, text=True, timeout=180, cwd=d)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-2000:])
    return "\n".join(l for l in r.stdout.splitlines() if "Warning" not in l).rstrip()


def cell(f, title):
    v, note = M[title][f]
    return f"{ICON[v].split()[0]} {note}"


def fw_page(f):
    i = FWINFO[f]
    others = " · ".join(f"[{o}]({FILE[o]}.html)" for o in FW if o != f)
    code = CODE[f].strip()
    if i["runs"] == "no":
        out_block = ("**Output:** not run. CrewAI's memory sends content to an embedding model and an LLM (OpenAI by "
                     "default) on every save, so it needs an API key. The code follows the current memory docs.")
    else:
        out = run(VENV if i["runs"] == "venv" else FW_PY, code)
        out_block = f"**Output** (from running the code above on {DATE}):\n\n```\n{out}\n```"
    note = ("_Illustrative example: made-up data, no ServiceApps instance. "
            + ("The code was run as shown; the model is a scripted stand-in, so no API key is needed._"
               if i["runs"] != "no" else "The code is written from the current docs but not run (it needs an API key)._"))
    rows = []
    for sec, titles in SECTION_OF.items():
        for t in titles:
            v, n = M[t][f]
            mark = " †" if t in NOTE_GENERAL else ""
            rows.append(f"| **{t}** | {ICON[v]} | {n}{mark} | [Deep dive]({SLUG[t]}.html) |")
    counts = {k: sum(1 for t in M if M[t][f][0] == k) for k in "RCY"}
    yours = "\n".join(f"- **{t}**: {M[t][f][1]}" for t in M if M[t][f][0] == "Y")
    comp = "\n".join(f"- **{t}**: {M[t][f][1]}" for t in M if M[t][f][0] == "C")
    steps = "\n".join(f"{k}. {s}" for k, s in enumerate(i["steps"], 1))
    watch = "\n".join(f"- {w}" for w in i["watch"])
    gives = "\n".join(f"- {g}" for g in i["gives"])
    trade = "\n".join(f"- {t}" for t in i["tradeoffs"])
    return f"""# Framework deep dive: {f} memory and the 27 solutions

{DATE} · Michael Chang · Status: {i['status']}

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · Other frameworks: {others}

**Read in this order**

1. [In plain words](#in-plain-words)
2. [What it gives you for memory](#what-it-gives-you-for-memory): from the current docs
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): code and output
4. [The 27 solutions with {f}](#the-27-solutions-with-{f.lower()}): replace, complement or still yours
5. [Use both: what you still build](#use-both-what-you-still-build)
6. [In NurseOps Now](#in-nurseops-now), [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

{i['plain']}

**In plain terms:** {i['plain_terms']}

## What it gives you for memory

From the official memory docs ([{f} memory docs]({DOCS[f]})), checked on {DATE}:

{gives}

:::highlight
## How to implement it (ServiceApps)

{note}

**The scenario.** {i['scenario']}

**Steps.**

{steps}

**The code** (Python):

```python
{code}
```

{out_block}

**What to watch for.**

{watch}
:::

## The 27 solutions with {f}

**🔁 Replace** = {f} does it, you configure it ({counts['R']} of 27). **🤝 Complement** = use both: {f} gives the mechanism, you add the rules ({counts['C']}). **🛠 Still yours** = build it yourself ({counts['Y']}). † = not a memory feature, so from general knowledge rather than the memory docs; check the current docs.

| Book solution | With {f} | How | Solution |
|---|---|---|---|
""" + "\n".join(rows) + f"""

## Use both: what you still build

**Still yours with {f}:**

{yours}

**Use both (complement), with your rules on top:**

{comp}

## In NurseOps Now

{i['nurseops']}

## Trade-offs

{trade}

## Interview answer

"{i['interview']}"

All data in this post is made up.

[← Back to all 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
"""


def section_table(sec):
    titles = SECTION_OF[sec]
    head = "| Book solution | Overall | " + " | ".join(f"[{f}](deep-dives/{FILE[f]}.html)" for f in FW) + " |"
    rows = [f"| **{t}**{' †' if t in NOTE_GENERAL else ''} | {M[t]['overall']} | " + " | ".join(cell(f, t) for f in FW) + " |"
            for t in titles]
    rep = sum(1 for t in titles if M[t]["overall"].startswith("🔁"))
    yours = sum(1 for t in titles if M[t]["overall"].startswith("🛠"))
    return f"""### With LangGraph, AutoGen, CrewAI and LlamaIndex ({TAG[sec]})

If you build on an agent framework, some of this section's solutions come built in. **🔁 Replace** = the framework does it, you configure it. **🤝 Complement** = use both: the framework gives the mechanism, you add the rules. **🛠 Still yours** = build it yourself. Each framework name links to its deep dive.

**In short:** of this section's {len(titles)} solutions, {rep} are mostly replaced by the frameworks, {yours} stay mostly yours, and the others are used together.

{head}
|---|---|---|---|---|---|
""" + "\n".join(rows) + f"""

_Memory features checked against each framework's official memory docs on {DATE}. † = not a memory feature, so from general knowledge; check the current docs._

"""


def put_section_tables(md):
    old = re.compile(r"### With LangGraph, AutoGen(?: and CrewAI|, CrewAI and LlamaIndex) \([^)]*\)\n.*?(?=\n### |\n## )", re.S)
    md = old.sub("", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    stops = {"intro": "\n## " + SECTIONS["71"][0], "71": "\n### Step 1:", "72": "\n### Step 4:",
             "73": "\n### Step 6:", "74": "\n### Step 10:"}
    for sec, stop in stops.items():
        assert md.count(stop) == 1, stop
        md = md.replace(stop, "\n" + section_table(sec).rstrip() + "\n" + stop, 1)
    return md


def main():
    assert FW_PY, "set FW_PYTHON to an env with autogen-agentchat, autogen-ext, llama-index-core"
    scratch = HERE / "fw_examples"                         # lg.py, ag.py, li.py (tested examples)
    for f, name in (("LangGraph", "lg.py"), ("AutoGen", "ag.py"), ("LlamaIndex", "li.py")):
        CODE[f] = (scratch / name).read_text()
    files = []
    for f in FW:
        p = OUT / f"{FILE[f]}.md"
        p.write_text(fw_page(f))
        files.append(str(p))
        print("wrote", p.name)
    PARENT.write_text(put_section_tables(PARENT.read_text()))
    print("parent: framework tables in 5 sections")
    subprocess.run([sys.executable, str(KIT), *files, str(PARENT), "--terms", str(BLOG / "terms.py")], check=True,
                   stdout=subprocess.DEVNULL)
    print("built 4 framework deep dives + parent")


if __name__ == "__main__":
    main()
