# Deep dive 5 of 27: Agentic Outcome: Hybrid Memory Systems

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Context and State Management (Intro)](../nurseops-now-state.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Agentic Outcome: Token Budgets](state-04-token-budgets.html) · [Agentic Outcome: Strict State Serialization →](state-06-strict-state-serialization.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Hybrid memory combines a short buffer of the latest messages with a search over long-term memory. The buffer keeps the flow of the conversation; the search brings back the one old fact or article that matters now.

**In plain terms:** remembering what someone just said, and also checking your notes from last month when they mention an old topic.

## The problem it solves

**LLMs are stateless** and **The context window: finite, expensive, volatile**: a buffer alone forgets old facts, and long-term search alone loses the thread of the conversation.

**What the book proposes** (in my words): couple a short-term conversational buffer with long-term vector retrieval (RAG).

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee says "it says error 809 on hotel Wi-Fi". ServiceApps Assist needs both the last few turns and the right KB article.

**Steps.**

1. Keep a fixed-size buffer of recent messages.
2. Keep long-term items (KB, saved notes) in a vector store.
3. On each question, take the buffer as-is and search long-term memory with the question.
4. Send both, clearly separated, to the model.

**The code** (Python):

```python
import math, re
from collections import Counter, deque

recent = deque(maxlen=4)                                 # short-term buffer: last 2 turns
def embed(t): return Counter(re.findall(r"[a-z0-9]+", t.lower()))
def cos(a, b):
    d = sum(a[w] * b[w] for w in a)
    n = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return d / n if n else 0.0

long_term = ["KB0010234 VPN error 809: avoid guest Wi-Fi, restart the client",
             "KB0030100 Printer setup on macOS: add the printer by IP address",
             "Saved note: the user often works from hotels"]

def context(question):
    q = embed(question)
    best = max(long_term, key=lambda d: cos(q, embed(d)))
    return {"recent": list(recent), "recalled": best}

for role, text in [("user", "Hi"), ("assistant", "Hello! How can I help?"), ("user", "VPN broke again"), ("assistant", "Which error?")]:
    recent.append(f"{role}: {text}")
c = context("it says error 809 on hotel wifi")
print("recent  :", c["recent"])
print("recalled:", c["recalled"])
```

**Output** (from running the code above):

```
recent  : ['user: Hi', 'assistant: Hello! How can I help?', 'user: VPN broke again', 'assistant: Which error?']
recalled: KB0010234 VPN error 809: avoid guest Wi-Fi, restart the client
```

**What to watch for.**

- Label the two parts in the prompt ("recent conversation" vs "retrieved knowledge") so the model treats retrieved text as data.
- Retrieved text can contain instructions; never follow them (see Input Filtering).
- Don't recall from other users' memories; filter first.

**In plain terms:** a short memory for the conversation, plus a quick look in the filing cabinet for the one old note that matters.
:::

## In NurseOps Now

Built. AI Assist sends the last 10 turns (the buffer) and lets the model call RAG tools over policies and the user guide (`search_policy`, `search_guide`) plus case lookups. See [Step 2](../nurseops-now-state.html#step-2-build-the-window) and [Step 3](../nurseops-now-state.html#step-3-load-facts-only-when-needed).

## Trade-offs

- Two memories mean two things to tune and test.
- Retrieval adds latency; caching popular articles helps.

## Interview answer

"I combine a small recent-messages buffer with retrieval over long-term memory. The buffer keeps the conversation coherent, retrieval brings back the specific article or fact the question needs, and both go into the prompt clearly labeled."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
