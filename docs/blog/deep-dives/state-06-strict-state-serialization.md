# Deep dive 6 of 27: Agentic Outcome: Strict State Serialization

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: 🟡 partly built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Context and State Management (Intro)](../nurseops-now-state.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Agentic Outcome: Hybrid Memory Systems](state-05-hybrid-memory-systems.html) · [Token Counting Middleware →](state-07-token-counting-middleware.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Serialization means saving the agent's full working state (which step it's on, what's done, what it learned) to disk after every step, so it can pause, crash and resume exactly where it left off, without redoing or losing work.

**In plain terms:** a video game save point after every level, so a power cut doesn't send you back to the start.

## The problem it solves

**No external state**: a crash or restart mid-task loses the progress, or worse, repeats a step that shouldn't run twice (like sending an email).

**The standard approach** (in my words): implement strict state serialization so agents can pause, crash and resume without data loss.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist runs a 4-step workflow on a ticket: triage, look up KB, draft a reply, send it. It crashes during the draft.

**Steps.**

1. Define the state as a small, typed object (step, done, facts).
2. Save it after every step, atomically (write a temp file, then rename).
3. On restart, load the state and continue from the saved step.
4. Make steps that touch the outside world (sending) run once, after everything else is saved.

**The code** (Python):

```python
import json, os, tempfile
from dataclasses import dataclass, asdict, field

@dataclass
class TicketWorkflow:
    ticket: str
    step: str = "triage"
    done: list = field(default_factory=list)

STEPS = ["triage", "lookup_kb", "draft_reply", "send"]
path = os.path.join(tempfile.mkdtemp(), "INC0012345.json")

def save(s):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(asdict(s), f)
    os.replace(tmp, path)                                # atomic: never a half-written file

def load():
    with open(path) as f:
        return TicketWorkflow(**json.load(f))

def run(s, crash_at=None):
    for name in STEPS[STEPS.index(s.step):]:
        if name == crash_at:
            raise RuntimeError(f"crashed during {name}")
        s.done.append(name)
        s.step = STEPS[STEPS.index(name) + 1] if name != "send" else "finished"
        save(s)
    return s

try:
    run(TicketWorkflow("INC0012345"), crash_at="draft_reply")
except RuntimeError as e:
    print("first run:", e)
s = load(); print("saved state:", s.step, s.done)
s = run(s); print("resumed:   ", s.step, s.done)
```

**Output** (from running the code above):

```
first run: crashed during draft_reply
saved state: draft_reply ['triage', 'lookup_kb']
resumed:    finished ['triage', 'lookup_kb', 'draft_reply', 'send']
```

**What to watch for.**

- Save after the step, never before, and make each step safe to repeat if it might run twice.
- Version the state format, so old saves still load after a code change.
- Don't save secrets or raw personal data in the state.

**In plain terms:** the workflow writes down 'done: triage, lookup' after each step, so after a crash it picks up at 'draft reply'.
:::

## In NurseOps Now

Partly built. AI Assist chat is checkpointed after every graph step by LangGraph's `SqliteSaver` and survives restarts (the parent post's demo). The case review workflow (`review_graph.py`) is not checkpointed mid-run: a crash reruns it from the start, which is safe because the case status only changes when it finishes. See [Step 1](../nurseops-now-state.html#step-1-pick-and-load-the-thread).

## Trade-offs

- Saving every step adds disk writes and a little latency.
- Resuming is only safe if steps are idempotent (safe to repeat).

## Interview answer

"I serialize the agent's state after every step, atomically, so a crash resumes at the last completed step instead of starting over or repeating side effects. In LangGraph that's a checkpointer keyed by thread ID; for a custom workflow it's a small typed state object written to disk."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
