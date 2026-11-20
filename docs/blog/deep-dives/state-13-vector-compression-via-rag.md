# Deep dive 13 of 27: Vector Compression via RAG

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: 🟡 documents only

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Compression Strategies: Summarization and Entity Extraction (7.2)](../nurseops-now-state.html#compression-strategies-summarization-and-entity-extraction-7-2) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Entity Extraction](state-12-entity-extraction.html) · [The Engineering Trade-off: Fidelity vs. Capacity →](state-14-engineering-trade-off-fidelity-vs-capacity.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Vector compression stores old conversation (or any long text) as embeddings outside the window, and brings back only the few pieces relevant to the current question. The AI can "remember" a long history while only a few hundred tokens are in the window.

**In plain terms:** instead of re-reading every old email, you search your mailbox and open the two that matter.

## The problem it solves

**History can't keep growing**: summaries lose detail, and you can't keep all old turns in the window.

**What the book proposes** (in my words): convert past text into embeddings in a vector database, and retrieve only relevant segments just in time.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee had a long chat weeks ago with their laptop tag and contact preference. Today they ask about both.

**Steps.**

1. When turns leave the window, embed and store them with user and thread labels.
2. On a new question, search only that user's stored turns.
3. Insert the top few results, labeled as "from earlier conversations".
4. Expire old memories (see TTL expiration).

**The code** (Python):

```python
import math, re
from collections import Counter
def embed(t): return Counter(re.findall(r"[a-z0-9]+", t.lower()))
def cos(a, b):
    d = sum(a[w] * b[w] for w in a)
    n = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return d / n if n else 0.0

old_turns = ["user: my laptop asset tag is LT-4471", "user: I work from the Berlin office on Tuesdays",
             "assistant: your VPN profile was reset on Monday", "user: I prefer email over phone calls"] + \
            [f"user: small talk number {i}" for i in range(30)]
memory = [(embed(t), t) for t in old_turns]            # stored outside the window

def recall(q, k=2):
    qv = embed(q)
    return [t for _, t in sorted(memory, key=lambda m: -cos(qv, m[0]))[:k]]

q = "what is my laptop asset tag and do I prefer email or phone"
print("old turns in memory:", len(memory), "| the window gets only:")
for t in recall(q):
    print("  ", t)
```

**Output** (from running the code above):

```
old turns in memory: 34 | the window gets only:
   user: my laptop asset tag is LT-4471
   user: I prefer email over phone calls
```

**What to watch for.**

- Search only the current user's memories.
- Old memories can be outdated; prefer recent ones and show their date.
- Retrieved turns are data, not instructions.

**In plain terms:** every old conversation goes into a searchable archive; each new question pulls out just the two lines it needs.
:::

## In NurseOps Now

Partly built: NurseOps Now uses vector search (Chroma) for policy text and the user guide, not for chat history. See the [ingestion deep dive](01-ingestion.html).

## Trade-offs

- Keeps far more history than a summary, but search can miss or surface stale memories.
- Storage and embedding costs grow with every conversation.

## Interview answer

"Old turns don't have to be summarized or dropped: I embed them into a per-user vector store and retrieve only what the new question needs, labeled as earlier conversation. It scales to long histories with a few hundred tokens of window."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
