# Deep dive 2 of 27: Three-Tier Memory: Long-Term (Vector Store)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (documents)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Context and State Management (Intro)](../nurseops-now-state-bk7.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Three-Tier Memory: Short-Term (Context Window)](state-01-short-term-context-window.html) · [Three-Tier Memory: Episodic (Experience Log) →](state-03-episodic-experience-log.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Long-term memory is knowledge kept outside the model that the AI can search when it needs it: help articles, past facts about a user, notes from earlier sessions. A vector store finds items by meaning, so "my VPN says 809" can find an article titled "Error 809".

**In plain terms:** a library with a librarian who understands what you mean, not just the exact title.

## The problem it solves

**No external state** and **The context window: finite, expensive, volatile**: anything only in the window is gone after the call, and you can't fit a whole knowledge base into it.

**The standard approach** (in my words): keep a long-term tier in a vector store and pull relevant items into the window only when a question needs them.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist should remember KB articles and a few saved preferences per employee, and recall the right one for a new question.

**Steps.**

1. Turn each item (KB section, saved preference) into a vector with an embedding model.
2. Store the vector with its text and labels (kind, user, KB, permissions).
3. At question time, embed the question and return the closest items, filtered by labels.
4. Put only the top results into the window.

**The code** (Python):

```python
import math, re
from collections import Counter

def embed(text):                 # stand-in for a real embedding model: word counts
    return Counter(re.findall(r"[a-z0-9]+", text.lower()))

def cosine(a, b):
    dot = sum(a[w] * b[w] for w in a)
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

store = []                       # long-term memory: (vector, text, labels)
def remember(text, **labels): store.append((embed(text), text, labels))
def recall(question, k=1, **where):
    q = embed(question)
    hits = [(cosine(q, v), t) for v, t, lab in store if all(lab.get(x) == y for x, y in where.items())]
    return sorted(hits, key=lambda h: -h[0])[:k]

remember("KB0010234: VPN error 809 means the client can't reach the server; avoid guest Wi-Fi.", kind="kb")
remember("KB0020311: Working abroad is allowed up to 10 working days a year.", kind="kb")
remember("User prefers answers in short bullet points.", kind="preference", user="u42")

for q, where in [("why does my vpn say error 809", {"kind": "kb"}), ("how should answers be formatted", {"user": "u42"})]:
    score, text = recall(q, **where)[0]
    print(f"{q!r} -> {score:.2f} {text}")
```

**Output** (from running the code above):

```
'why does my vpn say error 809' -> 0.27 KB0010234: VPN error 809 means the client can't reach the server; avoid guest Wi-Fi.
'how should answers be formatted' -> 0.17 User prefers answers in short bullet points.
```

**What to watch for.**

- Filter by labels (user, permissions) before ranking, so one user's memories never surface for another.
- Only store finalized, useful items; junk memories make search worse (vector store hygiene).
- Keep exact facts (ticket status, IDs) in SQL, not only in the vector store.

**In plain terms:** every saved note gets a meaning-based shelf location, and the assistant borrows only the one or two books it needs.
:::

## In NurseOps Now

Built for documents. Policy PDFs and the AI Assist user guide are chunked, embedded with all-MiniLM-L6-v2 and stored in Chroma (`backend/app/rag/index.py`), always filtered by CPT code. Chat itself is kept in checkpoints and case facts in SQL, not in the vector store. See the [ingestion deep dive](01-ingestion.html).

## Trade-offs

- Search by meaning is fuzzy: great for articles, wrong for exact facts like an ID.
- Every stored item costs an embedding and storage; be selective.

## Interview answer

"For long-term memory I use a vector store for knowledge that's searched by meaning, like KB articles, with labels for user and permissions applied before ranking. Exact facts go to SQL instead, because a similarity search can return a near match when you needed the exact record."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
