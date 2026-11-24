# Deep dive 3 of 27: Three-Tier Memory: Episodic (Experience Log)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Context and State Management (Intro)](../nurseops-now-state-bk7.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Three-Tier Memory: Long-Term (Vector Store)](state-02-long-term-vector-store.html) · [Agentic Outcome: Token Budgets →](state-04-token-budgets.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Episodic memory is the record of what happened, in order: who asked what, what the AI answered, what a person changed. It lets you replay a conversation, audit a decision and learn from mistakes.

**In plain terms:** a ship's logbook: every event, with a time and who did it.

## The problem it solves

**No external state**: without a log, you can't tell later why the AI said something or who changed a ticket, and the AI can't learn from past episodes.

**The standard approach** (in my words): keep a third tier, an append-only log of events, separate from the window and the knowledge store.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist logs every question, answer, thumbs up or down, and ticket status change, so support leads can replay any conversation.

**Steps.**

1. Write one row per event: time, actor, action, details.
2. Never edit rows; only append.
3. Tag each row with the conversation (thread) and ticket.
4. Replay an episode by filtering on the thread and sorting by time.

**The code** (Python):

```python
log = []
def record(actor, action, **details):
    log.append({"at": f"2026-11-19T10:{len(log):02d}:00Z", "actor": actor, "action": action, **details})

record("u42", "asked", question="VPN error 809", thread="u42:INC0012345")
record("assist", "answered", sources=["KB0010234"], thread="u42:INC0012345")
record("u42", "feedback", rating="thumbs_down", thread="u42:INC0012345")
record("agent7", "status_change", ticket="INC0012345", old="New", new="In Progress")

def episode(thread):             # replay one conversation in order
    return [e for e in log if e.get("thread") == thread]

for e in episode("u42:INC0012345"):
    print(e["at"], e["actor"], e["action"], {k: v for k, v in e.items() if k not in ("at", "actor", "action", "thread")})
print("all events:", len(log))
```

**Output** (from running the code above):

```
2026-11-19T10:00:00Z u42 asked {'question': 'VPN error 809'}
2026-11-19T10:01:00Z assist answered {'sources': ['KB0010234']}
2026-11-19T10:02:00Z u42 feedback {'rating': 'thumbs_down'}
all events: 4
```

**What to watch for.**

- Mask personal data before it's logged (see Sanitization layer).
- Logs grow forever; set retention (see TTL expiration).
- Turn bad episodes (thumbs down) into test questions, so the log improves the system.

**In plain terms:** the assistant's diary: nothing is rewritten, so you can always see what really happened.
:::

## In NurseOps Now

Built. The `audit_log` table records every status change, AI Assist question and clear; `llm_calls` records each AI call's tokens and cost; and LangSmith traces each run with a masked thread ID. See [Step 7](../nurseops-now-state-bk7.html#step-7-case-state-machine) and [Step 9](../nurseops-now-state-bk7.html#step-9-forget-on-request).

## Trade-offs

- Detailed logs help audits and debugging but are a privacy risk if not masked.
- Append-only is trustworthy but needs a retention policy.

## Interview answer

"I keep an episodic log separate from chat memory: one append-only row per event with time, actor and action. It answers 'why did the AI say that' and 'who changed this', and bad episodes become new test cases."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
