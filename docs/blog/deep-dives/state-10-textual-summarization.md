# Deep dive 10 of 27: Textual Summarization

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ⬜ not built (illustrative)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Compression Strategies: Summarization and Entity Extraction (7.2)](../nurseops-now-state.html#compression-strategies-summarization-and-entity-extraction-7-2) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← System Prompt Pinning](state-09-system-prompt-pinning.html) · [Rolling Summaries →](state-11-rolling-summaries.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Textual summarization rewrites an old conversation into a few short lines that keep the facts and decisions and drop the chat filler ("hi", "thanks", "sure"). The summary goes into the window instead of the full chat.

**In plain terms:** meeting minutes instead of the full recording.

## The problem it solves

**History can't keep growing**: a long chat fills the window with greetings and back-and-forth that carry no facts.

**The standard approach** (in my words): periodically rewrite the history into a dense narrative that keeps only the state changes.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee and ServiceApps Assist fixed a printer problem in 8 turns. Before the next topic, the chat is condensed.

**Steps.**

1. Pick the turns to summarize (for example, everything older than the last 4).
2. Ask the model: "Rewrite as short facts and decisions; keep IDs, numbers and errors exactly."
3. Replace those turns with the summary.
4. Keep exact IDs and decisions in structured storage too (see The Engineering Trade-off).

**The code** (Python):

```python
import re
FILLER = re.compile(r"^(thanks for waiting|thank you|thanks|hello|hi there|hi|okay|ok|sure|great|no problem)\b[.!,]?\s*", re.I)
chat = [("user", "Hi there!"), ("assistant", "Hello! How can I help you today?"),
        ("user", "My laptop can't print to the 3rd floor printer."),
        ("assistant", "Sorry to hear that. Let me check that for you, one moment please."),
        ("user", "Sure, no rush."), ("assistant", "Thanks for waiting! Is it the printer named PR-3F-01?"),
        ("user", "Yes, PR-3F-01."), ("assistant", "Okay. Please remove it, then add it again by IP 10.20.3.15 (KB0030100)."),
        ("user", "Okay, give me a minute to try that."), ("assistant", "Of course, take your time."),
        ("user", "Thanks, that worked!"), ("assistant", "Great, glad it's fixed. Anything else I can help with?"),
        ("user", "No, that's all, thank you so much!"), ("assistant", "You're welcome, have a great day!")]

def summarize(turns):
    """Stand-in for an AI call ('rewrite as short facts and decisions'): keep only fact-bearing lines, no roles."""
    facts = []
    for role, text in turns:
        t = FILLER.sub("", text).strip()
        if re.search(r"\d|KB\d+|worked|can't|failed", t) and t not in facts:
            facts.append(t)
    return "Facts: " + " | ".join(facts)

s = summarize(chat)
print(s)
print(f"{sum(len(t) for _, t in chat)} chars -> {len(s)} chars")
```

**Output** (from running the code above):

```
Facts: My laptop can't print to the 3rd floor printer. | Is it the printer named PR-3F-01? | Yes, PR-3F-01. | Please remove it, then add it again by IP 10.20.3.15 (KB0030100). | that worked!
507 chars -> 190 chars
```

**What to watch for.**

- Tell the summarizer to copy IDs, numbers and error codes exactly; summaries love to round them off.
- Never summarize a summary repeatedly without checking it (see Hallucination drift).
- Keep the full chat on disk for audits.

**In plain terms:** after a long call, write three lines in the ticket: what broke, what fixed it, which article helped.
:::

## In NurseOps Now

Not built. NurseOps Now doesn't summarize: turns older than the last 10 stay on disk and leave the window, and case facts never depend on chat because they're in SQL. This is [Plan 2](../nurseops-now-state.html#plan-closing-the-gaps).

## Trade-offs

- Saves a lot of window, but every summary loses detail and costs an AI call.
- Errors in a summary are hard to spot later.

## Interview answer

"When history gets long I'd rewrite old turns into short facts and decisions, with an instruction to copy IDs and error codes exactly, and keep the full transcript on disk. Exact facts also live in structured storage, so a bad summary can't corrupt them."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
