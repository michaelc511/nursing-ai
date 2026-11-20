# Deep dive 18 of 27: Session Caching (Redis/Key-Value)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (SQLite, not Redis)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)](state-17-semantic-storage-vector-db.html) · [The Rehydration Pattern →](state-19-rehydration-pattern.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Session caching saves a conversation's whole state (history and current step) under a session ID in a fast key-value store. If the user closes the browser and comes back, the session is loaded and the conversation continues.

**In plain terms:** a coat check: you get a ticket number, and your coat is waiting when you come back.

## The problem it solves

**Summarization solves volume, not time**: closing the tab or a server restart loses the conversation unless it's saved somewhere.

**What the book proposes** (in my words): serialize the chat history and current state into a JSON blob stored by session ID (for example in Redis), enabling pause-and-resume and episodic recall.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee is halfway through a VPN troubleshooting chat, closes the browser, and comes back later.

**Steps.**

1. Pick a session ID (for example user + ticket).
2. After each turn, save the state as JSON under that key, with an expiry.
3. On return, load by session ID; start fresh if it's missing or expired.
4. Clear the key when the conversation ends or the user asks.

**The code** (Python):

```python
import json, time
class KV:                                        # stand-in for Redis: SET key value EX seconds / GET key
    def __init__(self): self.d = {}
    def set(self, k, v, ex=None): self.d[k] = (v, time.time() + ex if ex else None)
    def get(self, k):
        v, exp = self.d.get(k, (None, None))
        if exp and time.time() > exp:
            self.d.pop(k, None); return None
        return v

r = KV()
def save_session(sid, state): r.set(f"session:{sid}", json.dumps(state), ex=3600)
def load_session(sid):
    raw = r.get(f"session:{sid}")
    return json.loads(raw) if raw else {"history": [], "step": "start"}

sid = "u42:INC0012345"
s = load_session(sid); print("new session:", s)
s["history"] += ["user: VPN error 809", "assistant: are you on guest Wi-Fi?"]
s["step"] = "waiting_for_user"
save_session(sid, s)
print("browser closed ... user returns")
print("resumed    :", load_session(sid))
```

**Output** (from running the code above):

```
new session: {'history': [], 'step': 'start'}
browser closed ... user returns
resumed    : {'history': ['user: VPN error 809', 'assistant: are you on guest Wi-Fi?'], 'step': 'waiting_for_user'}
```

**What to watch for.**

- Mask personal data before caching (see Sanitization layer).
- Set an expiry on every key.
- One session per user and ticket, so conversations never mix.

**In plain terms:** the conversation is checked in under your ticket number and handed back when you return.
:::

## In NurseOps Now

Built with SQLite instead of Redis: LangGraph's `SqliteSaver` checkpoints each AI Assist thread (`nurse1:case-3`) after every step in `assist_memory.db`, and it survives restarts. Expiry isn't built yet ([Plan 3](../nurseops-now-state.html#plan-closing-the-gaps)). See [Step 1](../nurseops-now-state.html#step-1-pick-and-load-the-thread).

## Trade-offs

- Redis is fast and has built-in expiry but is another service to run; SQLite is simpler for one server.
- Caching full history grows; pair it with compression.

## Interview answer

"Each conversation is saved under a session ID, user plus ticket, as a small JSON state with an expiry, after every turn. Closing the tab or restarting the server doesn't lose anything; the next message just reloads it."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
