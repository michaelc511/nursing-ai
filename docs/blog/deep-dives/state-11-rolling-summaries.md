# Deep dive 11 of 27: Rolling Summaries

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ⬜ not built (illustrative)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Compression Strategies: Summarization and Entity Extraction (7.2)](../nurseops-now-state-bk7.html#compression-strategies-summarization-and-entity-extraction-7-2) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Textual Summarization](state-10-textual-summarization.html) · [Entity Extraction →](state-12-entity-extraction.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Rolling summaries do summarization automatically and continuously: every few turns, the oldest turns are folded into a running summary and removed from the window. Recent turns stay word for word; older ones become a growing short summary.

**In plain terms:** a notebook where you keep today's notes in full and boil each older page down to one line.

## The problem it solves

**History can't keep growing**: you need the conversation to go on for a long time without the window filling up.

**The standard approach** (in my words): after every N turns, a background job condenses the oldest turns into a bulleted list of facts and decisions, so recent history stays detailed and older history gets more condensed.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** A ServiceApps Assist chat runs 12 turns. The window keeps 4 recent turns; every 4 turns, the oldest 4 are folded into the summary.

**Steps.**

1. Choose how many recent turns to keep word for word (N_KEEP) and how often to fold (EVERY).
2. When the window holds N_KEEP + EVERY turns, fold the oldest EVERY turns into the summary.
3. Send: rules, the summary, then the recent turns.
4. Run the folding in the background, so the user doesn't wait.

**The code** (Python):

```python
N_KEEP, EVERY = 4, 4
summary, window, folded = "", [], 0

def fold(old):                                   # stand-in for an AI summary of the oldest turns
    return "; ".join(t.split(":", 1)[1].strip() for t in old)

for i in range(1, 13):
    window.append(f"turn {i}: fact {i}")
    if len(window) >= N_KEEP + EVERY:
        old, window = window[:EVERY], window[EVERY:]
        summary = (summary + "; " if summary else "") + fold(old)
        folded += len(old)
        print(f"after turn {i:2d}: summary covers {folded} turns, window holds {len(window)}")

print("summary:", summary)
print("window :", window)
```

**Output** (from running the code above):

```
after turn  8: summary covers 4 turns, window holds 4
after turn 12: summary covers 8 turns, window holds 4
summary: fact 1; fact 2; fact 3; fact 4; fact 5; fact 6; fact 7; fact 8
window : ['turn 9: fact 9', 'turn 10: fact 10', 'turn 11: fact 11', 'turn 12: fact 12']
```

**What to watch for.**

- Summarize the summary only rarely, and check it against the stored facts.
- Fold in the background, but never send a half-updated summary.
- Keep the original turns on disk.

**In plain terms:** the last few messages stay sharp; everything older becomes a short running recap at the top.
:::

## In NurseOps Now

Not built. Older turns are dropped from the window but kept on disk ([Step 5](../nurseops-now-state-bk7.html#step-5-older-turns)); a rolling summary of what the nurse said is [Plan 2](../nurseops-now-state-bk7.html#plan-closing-the-gaps).

## Trade-offs

- Long conversations stay usable, but every fold is a chance to lose or bend a detail.
- Background jobs add moving parts.

## Interview answer

"I'd keep the last few turns verbatim and fold older ones into a running summary every few turns, in the background. The prompt becomes rules, summary, recent turns. Exact facts stay in structured storage, so the summary only has to carry the conversational context."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
