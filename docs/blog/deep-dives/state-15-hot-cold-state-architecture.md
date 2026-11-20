# Deep dive 15 of 27: The Hot/Cold State Architecture

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← The Engineering Trade-off: Fidelity vs. Capacity](state-14-engineering-trade-off-fidelity-vs-capacity.html) · [Structured Storage (SQL/Postgres) →](state-16-structured-storage-sql-postgres.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Hot state is what the AI is working with right now, in memory for this call. Cold state is what's saved in a database for later: preferences, history, finished tasks. Each call loads the bit of cold state it needs into hot state, and saves what matters back.

**In plain terms:** hot is what's on your desk today; cold is the filing cabinet.

## The problem it solves

**Summarization solves volume, not time**: if everything lives in the window, a crash, a closed tab or a new session loses it.

**What the book proposes** (in my words): separate hot state (context window and RAM: fast, volatile, current reasoning) from cold state (SQL, NoSQL or a vector database: durable, slower, long-term facts).

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist answers "Is my laptop under warranty?" using a saved profile, with scratch notes that are thrown away after the call.

**Steps.**

1. Keep a cold store (a database) for facts that must survive.
2. At the start of a call, load the needed cold facts into hot state.
3. Keep scratch reasoning hot only.
4. At the end, write back what should be remembered and clear hot state.

**The code** (Python):

```python
import sqlite3, json
cold = sqlite3.connect(":memory:")               # stand-in for the database
cold.execute("create table facts(user text, key text, value text, primary key(user, key))")
hot = {}                                         # in RAM: this call only

def remember(user, key, value):
    cold.execute("insert or replace into facts values(?,?,?)", (user, key, json.dumps(value)))

def start_call(user, question):
    hot.clear()
    hot["question"] = question
    hot["profile"] = {k: json.loads(v) for k, v in cold.execute("select key, value from facts where user=?", (user,))}
    hot["scratch"] = []

def end_call():
    hot.clear()

remember("u42", "preferred_contact", "email"); remember("u42", "asset", "LT-4471")
start_call("u42", "Is my laptop under warranty?")
hot["scratch"].append("look up the warranty for LT-4471")
print("hot during the call:", hot)
end_call()
print("hot after the call :", hot)
print("cold (kept)        :", cold.execute("select key, value from facts").fetchall())
```

**Output** (from running the code above):

```
hot during the call: {'question': 'Is my laptop under warranty?', 'profile': {'asset': 'LT-4471', 'preferred_contact': 'email'}, 'scratch': ['look up the warranty for LT-4471']}
hot after the call : {}
cold (kept)        : [('preferred_contact', '"email"'), ('asset', '"LT-4471"')]
```

**What to watch for.**

- Load only what the call needs from cold state, not everything about the user.
- Decide explicitly what gets written back; scratch work usually shouldn't.
- Cold state holds personal data; protect and expire it.

**In plain terms:** take the one file you need out of the cabinet, work on it, file the result, clear the desk.
:::

## In NurseOps Now

Built. Hot = the window built per call; cold = SQLite (cases, reviews, decisions, audit), LangGraph checkpoints for chat, and Chroma for policies. See the [Intro](../nurseops-now-state.html#context-and-state-management-intro) and [Step 1](../nurseops-now-state.html#step-1-pick-and-load-the-thread).

## Trade-offs

- Cold reads add latency; cache hot items that repeat.
- Two places for state means a clear rule for what goes where.

## Interview answer

"I split memory into hot state for the current call and cold state in a database. Each call loads only what it needs from cold storage, does its work in memory, and writes back what should be remembered, so restarts and new sessions lose nothing."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
