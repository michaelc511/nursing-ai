# Deep dive 4 of 27: Agentic Outcome: Token Budgets

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: 🟡 partly built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Context and State Management (Intro)](../nurseops-now-state-bk7.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Three-Tier Memory: Episodic (Experience Log)](state-03-episodic-experience-log.html) · [Agentic Outcome: Hybrid Memory Systems →](state-05-hybrid-memory-systems.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

A token budget decides, before each call, how much of the window each part may use: the rules, tool results, history, and room for the answer. Without a plan, one big tool result or a long chat silently crowds out everything else.

**In plain terms:** a monthly budget with a line for rent, food and savings, instead of spending until the money runs out.

## The problem it solves

**The context window: finite, expensive, volatile** and **Flooding the context window**: everything competes for one fixed space, and the part that loses is usually the rules or the answer.

**The standard approach** (in my words): engineer the window like a budget, compressing and summarizing progressively as it fills.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist has a long chat and three large KB/ticket results to include. Each zone gets a share of an 8,000-token window.

**Steps.**

1. Pick the model's window size and reserve room for the answer first.
2. Give each zone a share (rules, tool results, history, answer).
3. Fill each zone newest or most relevant first, stopping at its limit.
4. Log what was dropped, so you can tune the shares.

**The code** (Python):

```python
CONTEXT = 8000                                          # small on purpose for the example
SHARE = {"system": 0.10, "tools": 0.35, "history": 0.30, "answer": 0.25}
def tokens(text): return -(-len(text) // 4)             # rough: ~4 characters per token

def fit(items, limit):                                   # keep the newest items that fit
    kept, used = [], 0
    for it in reversed(items):
        t = tokens(it)
        if used + t > limit:
            break
        kept.insert(0, it); used += t
    return kept, used

limits = {k: int(CONTEXT * v) for k, v in SHARE.items()}
history = [f"turn {i:02d}: " + "x" * 600 for i in range(1, 21)]                     # 20 turns of ~150 tokens
tool_results = ["KB0010234 " + "y" * 3000, "INC0012345 " + "z" * 4000, "KB0020311 " + "w" * 9000]
h, hu = fit(history, limits["history"])
t, tu = fit(tool_results, limits["tools"])
print("limits:", limits)
print(f"history: kept {len(h)} of {len(history)} turns ({hu} tokens), oldest kept: {h[0][:8]}")
print(f"tools:   kept {len(t)} of {len(tool_results)} results ({tu} tokens): {[x.split()[0] for x in t]}")
print("answer room reserved:", limits["answer"], "tokens")
```

**Output** (from running the code above):

```
limits: {'system': 800, 'tools': 2800, 'history': 2400, 'answer': 2000}
history: kept 15 of 20 turns (2295 tokens), oldest kept: turn 06:
tools:   kept 1 of 3 results (2253 tokens): ['KB0020311']
answer room reserved: 2000 tokens
```

**What to watch for.**

- Rank tool results by relevance, not by order; the example keeps the newest only to stay short.
- Use the provider's token-counting API for real numbers; 4 characters per token is only a rough guide.
- Always reserve answer room, or long inputs cut the answer off.

**In plain terms:** each part of the prompt gets its own envelope of money, and nothing can borrow from the rules or the answer.
:::

## In NurseOps Now

Partly built. NurseOps Now limits by count, not tokens: the last 10 turns, questions cut at 2,000 characters, each tool result at 12,000 characters, at most 4 tool rounds, and a fixed `max_tokens` for the answer. Token usage is recorded after each call, but there is no budget check before it ([Plan 1](../nurseops-now-state-bk7.html#plan-closing-the-gaps)).

## Trade-offs

- Fixed shares are simple but waste space when one zone is empty; dynamic sharing is better but harder to test.
- Dropping is cheap; summarizing keeps more but costs an extra AI call.

## Interview answer

"I budget the window like money: reserve room for the answer, give rules, tools and history fixed shares, and fill each zone by relevance up to its limit. It stops one huge tool result from pushing out the rules, and the logs show what got dropped."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
