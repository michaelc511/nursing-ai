# Deep dive 14 of 27: The Engineering Trade-off: Fidelity vs. Capacity

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Compression Strategies: Summarization and Entity Extraction (7.2)](../nurseops-now-state-bk7.html#compression-strategies-summarization-and-entity-extraction-7-2) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Vector Compression via RAG](state-13-vector-compression-via-rag.html) · [The Hot/Cold State Architecture →](state-15-hot-cold-state-architecture.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Every compression trades fidelity (exact detail) for capacity (fitting more). The fix is to split what you remember: exact facts ("hard state": IDs, numbers, error codes) are stored word for word, and only the soft parts (intent, mood, flow) are summarized.

**In plain terms:** you can summarize how a meeting felt, but you copy the contract number exactly.

## The problem it solves

**Hallucination drift**: summaries are lossy, and a summary of a summary drifts like a game of telephone. An error code that becomes "an access error" is useless.

**The standard approach** (in my words): keep hard state in a lossless format (a SQL row or JSON block), summarize only soft state, and never summarize code blocks or error logs.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** A ServiceApps Assist chat about a failed software install contains an error code, an asset tag and a ticket number.

**Steps.**

1. Detect hard values with patterns or extraction (error codes, IDs, numbers, versions).
2. Store them exactly, as structured fields.
3. Summarize only the rest.
4. Send both: the exact values, then the summary.

**The code** (Python):

```python
import re
turns = ["Error code 0x80070005 when installing Teams", "Asset LT-4471, ticket INC0012345",
         "User sounds frustrated, wants a fix before Friday's demo", "Tried: reinstall, reboot, cleared cache"]

def careless_summary(t):                         # what a lossy summary can do to exact values
    return "User had an access error installing Teams on their laptop and is frustrated; a ticket exists."

HARD = re.compile(r"0x[0-9A-Fa-f]+|INC\d+|[A-Z]{2}-\d{4}")
def split_state(turns):
    hard = sorted({m for t in turns for m in HARD.findall(t)})
    soft = "Frustrated; wants a fix before Friday's demo; tried reinstall, reboot and clearing the cache."
    return {"hard": hard, "soft": soft}

s, st = careless_summary(turns), split_state(turns)
print("careless summary keeps:", [v for v in ["0x80070005", "INC0012345", "LT-4471"] if v in s])
print("hard state (exact)    :", st["hard"])
print("soft state (summary)  :", st["soft"])
```

**Output** (from running the code above):

```
careless summary keeps: []
hard state (exact)    : ['0x80070005', 'INC0012345', 'LT-4471']
soft state (summary)  : Frustrated; wants a fix before Friday's demo; tried reinstall, reboot and clearing the cache.
```

**What to watch for.**

- Decide upfront which fields are hard state; don't leave it to the summarizer.
- Code blocks and logs go to a file or blob, referenced by name, never paraphrased.
- Re-check summaries against hard state when you can.

**In plain terms:** copy the error code and ticket number exactly into the ticket; it's fine to paraphrase how the user felt.
:::

## In NurseOps Now

Built, more strictly: nothing is summarized at all. Case status, decisions, the AI review and audit rows are SQL records stored as-is, and tool errors are returned raw. See [Step 4](../nurseops-now-state-bk7.html#step-4-hard-state-stays-in-sql).

## Trade-offs

- Keeping hard state separate is more design work, but it removes a whole class of silent errors.
- Soft summaries still lose nuance.

## Interview answer

"Compression always costs fidelity, so I split state: hard values like IDs, error codes and decisions are stored exactly in structured fields, and only the soft conversational context is summarized. Code and logs are never paraphrased; they're stored and referenced."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
