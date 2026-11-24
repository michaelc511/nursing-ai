# Deep dive 19 of 27: The Rehydration Pattern

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state-bk7.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Session Caching (Redis/Key-Value)](state-18-session-caching-redis-key-value.html) · [Sanitization layer →](state-20-sanitization-layer.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Rehydration is how a returning user's context is rebuilt: fetch what's saved about them, filter it down to what matters for this question, and inject it into the prompt. To the user it feels like the AI remembers; really, the app assembled a new prompt from saved state.

**In plain terms:** before a follow-up meeting you pull the client's file, skim the open items, and walk in prepared.

## The problem it solves

**Summarization solves volume, not time**: a user who returns after a week expects the assistant to know their open tickets and preferences.

**The standard approach** (in my words): Fetch (query by user or session ID) → Filter (only active projects, recent summaries, relevant memories) → Inject (prepend to the system prompt of the new session).

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee comes back a week later and asks "Is my VPN ticket fixed yet?"

**Steps.**

1. Fetch: load the user's saved profile, tickets and summaries by user ID.
2. Filter: keep only open tickets and the latest summary.
3. Inject: add them to the prompt as a clearly labeled block.
4. Let tools fetch anything else on demand.

**The code** (Python):

```python
import json
db = {"u42": {"profile": {"contact": "email", "asset": "LT-4471"},
              "tickets": [{"number": "INC0012345", "status": "In Progress", "summary": "VPN 809 on hotel Wi-Fi"},
                          {"number": "INC0011000", "status": "Resolved", "summary": "Printer PR-3F-01 re-added"}],
              "summaries": ["2026-11-12: set up MFA", "2026-11-18: VPN 809, told to avoid guest Wi-Fi"]}}

def fetch(user): return db.get(user, {})
def filter_(state):
    return {"profile": state["profile"],
            "open_tickets": [t for t in state["tickets"] if t["status"] != "Resolved"],
            "latest": state["summaries"][-1:]}
def inject(base, ctx): return base + "\n\nWhat you know about this user:\n" + json.dumps(ctx, indent=1)

print(inject("You are ServiceApps Assist.", filter_(fetch("u42"))))
```

**Output** (from running the code above):

```
You are ServiceApps Assist.

What you know about this user:
{
 "profile": {
  "contact": "email",
  "asset": "LT-4471"
 },
 "open_tickets": [
  {
   "number": "INC0012345",
   "status": "In Progress",
   "summary": "VPN 809 on hotel Wi-Fi"
  }
 ],
 "latest": [
  "2026-11-18: VPN 809, told to avoid guest Wi-Fi"
 ]
}
```

**What to watch for.**

- Filter hard: injecting everything about a user wastes the window and leaks old data.
- Label the injected block as data, so the model doesn't treat it as instructions.
- Fetch live facts (ticket status) at question time, not from an old summary.

**In plain terms:** before answering, the assistant pulls your file, keeps the open tickets, and reads them first.
:::

## In NurseOps Now

Built: AI Assist fetches the thread by ID from the checkpointer, filters to the last 10 turns, and injects them with the rules; case facts come live from tools. See [Step 1](../nurseops-now-state-bk7.html#step-1-pick-and-load-the-thread), [Step 2](../nurseops-now-state-bk7.html#step-2-build-the-window) and [Step 3](../nurseops-now-state-bk7.html#step-3-load-facts-only-when-needed).

## Trade-offs

- The filter decides what the AI "remembers"; too strict and it seems forgetful, too loose and it's slow and noisy.
- Stale summaries can contradict live data; prefer live lookups.

## Interview answer

"Memory across sessions is rehydration: fetch the user's saved state by ID, filter to what's relevant (open tickets, the latest summary), and inject it as a labeled block. Live facts still come from tools, so nothing stale overrides the current status."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
