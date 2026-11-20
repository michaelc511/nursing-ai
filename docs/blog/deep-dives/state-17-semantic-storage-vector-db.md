# Deep dive 17 of 27: Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (Chroma)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Structured Storage (SQL/Postgres)](state-16-structured-storage-sql-postgres.html) · [Session Caching (Redis/Key-Value) →](state-18-session-caching-redis-key-value.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Semantic storage is a vector database: it stores text as embeddings and finds items by meaning. It's the right place for knowledge where an approximate match is fine, like help articles, notes and documentation.

**In plain terms:** asking "something about my slow notebook" and getting the article titled "Computer running slow".

## The problem it solves

**Summarization solves volume, not time**: knowledge must live outside the window, and people never phrase questions like the article titles.

**What the book proposes** (in my words): store unstructured knowledge (PDFs, email threads, meeting notes, documentation) in a vector database and retrieve by semantic relevance.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee types "my notebook is sluggish". The KB article is called "Computer running slow". Some articles are only for executives.

**Steps.**

1. Chunk documents and embed each chunk.
2. Store each vector with metadata: KB, category, who can read it.
3. Search with metadata filters (KB, permissions) first, then rank by similarity.
4. Return the top chunks with their IDs for citation.

**The code** (Python):

```python
import math, re
from collections import Counter
SYN = {"laptop": "computer", "notebook": "computer", "pc": "computer", "wifi": "network", "wireless": "network",
       "sluggish": "slow"}
def embed(t):                                    # stand-in for a real embedding model (synonyms ~ meaning)
    return Counter(SYN.get(w, w) for w in re.findall(r"[a-z0-9]+", t.lower()))
def cos(a, b):
    d = sum(a[w] * b[w] for w in a)
    n = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return d / n if n else 0.0

docs = [{"id": "KB0040001", "text": "Computer running slow: close browser tabs and restart", "kb": "IT", "can_read": "all"},
        {"id": "KB0040002", "text": "Wireless network drops in meeting rooms", "kb": "IT", "can_read": "all"},
        {"id": "KB0090007", "text": "Executive laptop refresh schedule", "kb": "IT", "can_read": "executives"},
        {"id": "KB0020311", "text": "Remote work policy: working abroad", "kb": "HR", "can_read": "all"}]
index = [(embed(d["text"]), d) for d in docs]

def search(q, kb=None, groups=("all",), k=2):
    qv = embed(q)
    hits = [(cos(qv, v), d) for v, d in index if (kb is None or d["kb"] == kb) and d["can_read"] in groups]
    return [(s, d) for s, d in sorted(hits, key=lambda h: -h[0])[:k] if s > 0]

for s, d in search("my notebook is sluggish", kb="IT"):
    print(f"{s:.2f} {d['id']} {d['text']}")
print("as an executive :", [d["id"] for _, d in search("laptop refresh", groups=("all", "executives"))])
print("as everyone else:", [d["id"] for _, d in search("laptop refresh")])
```

**Output** (from running the code above):

```
0.35 KB0040001 Computer running slow: close browser tabs and restart
as an executive : ['KB0090007', 'KB0040001']
as everyone else: ['KB0040001']
```

**What to watch for.**

- Apply permission filters inside the search, never after showing results.
- Store chunk IDs and section titles so answers can cite them.
- Re-index when an article changes; delete chunks of retired articles.

**In plain terms:** a search that understands what you mean, but only looks on the shelves you're allowed to see.
:::

## In NurseOps Now

Built on Chroma (pgvector planned for production): policy chunks with metadata (CPT, version, section, page), searched only within the case's policy, plus a separate collection for the user guide. See the [ingestion deep dive](01-ingestion.html).

## Trade-offs

- Great recall for fuzzy questions, but similar isn't the same as correct; keep exact facts in SQL.
- Hosted vector databases (Pinecone, Weaviate) scale further; local ones (Chroma) are simpler.

## Interview answer

"Documentation and notes go in a vector database with metadata such as KB, category and read permissions. Search filters on permissions first, then ranks by meaning, and returns chunk IDs so every answer can cite its article."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
