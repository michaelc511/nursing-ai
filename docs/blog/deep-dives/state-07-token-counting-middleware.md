# Deep dive 7 of 27: Token Counting Middleware

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ⬜ not built (illustrative)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Implementing Short-Term Memory: Token Budgets and Window Management (7.1)](../nurseops-now-state-bk7.html#implementing-short-term-memory-token-budgets-and-window-management-7-1) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Agentic Outcome: Strict State Serialization](state-06-strict-state-serialization.html) · [Dynamic Context Loading →](state-08-dynamic-context-loading.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Token counting middleware is a small check that runs before every AI call: it counts how full the window is and decides what to do, from "send as is" to "summarize now". It turns a silent failure into a planned one.

**In plain terms:** a fuel gauge with warning lights at 70%, 85% and 95%, instead of finding out when the engine stops.

## The problem it solves

**The token window is a hard limit**, **Sliding window truncation** and **Worse answers near capacity**: without counting, you only find out the window is full when something gets cut or the answers get worse.

**The standard approach** (in my words): put a pre-flight token check before every API call, with thresholds that trigger stronger compression as the window fills.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** A long ServiceApps Assist chat grows to 43 messages against a 4,000-token window.

**Steps.**

1. Count the tokens of everything you're about to send (use the provider's count-tokens API in production).
2. Compare with the model's limit and pick a level: OK, NOTICE (70%), WARNING (85%), CRITICAL (95%).
3. Act per level: drop old turns, summarize, or summarize hard and trim tool output.
4. Log the level and action for every call.

**The code** (Python):

```python
LIMIT = 4000
def count_tokens(messages):                     # rough: ~4 characters per token; use the real API in production
    return sum(-(-len(m["content"]) // 4) for m in messages)

def check_budget(messages, limit=LIMIT):
    u = count_tokens(messages) / limit
    if u > 0.95: return u, "CRITICAL", "summarize hard, trim tool output"
    if u > 0.85: return u, "WARNING", "summarize the oldest turns"
    if u > 0.70: return u, "NOTICE", "drop the oldest turns"
    return u, "OK", "send as is"

def middleware(messages, send):
    u, level, action = check_budget(messages)
    print(f"{len(messages):3d} msgs  {u:5.0%}  {level:8s} -> {action}")
    if level in ("WARNING", "CRITICAL"):
        messages = messages[-6:]                 # stand-in for summarizing
    return send(messages)

chat = []
for i in range(1, 44):
    chat.append({"role": "user", "content": "x" * 360})
    if i in (10, 20, 33, 38, 43):
        middleware(list(chat), send=lambda m: len(m))
```

**Output** (from running the code above):

```
 10 msgs    22%  OK       -> send as is
 20 msgs    45%  OK       -> send as is
 33 msgs    74%  NOTICE   -> drop the oldest turns
 38 msgs    86%  WARNING  -> summarize the oldest turns
 43 msgs    97%  CRITICAL -> summarize hard, trim tool output
```

**What to watch for.**

- Count everything: rules, tools' descriptions, tool results and history, not just the chat.
- Tune thresholds per model; 70/85/95 are a starting point, not a standard.
- Make the action visible in logs, so you can see how often it fires.

**In plain terms:** before every call, glance at the fuel gauge and decide whether to keep driving, refuel, or stop.
:::

## In NurseOps Now

Not built. NurseOps Now records input and output tokens after each call (`llm_calls` table), but nothing counts them before the call; the window is limited by turns instead. This is [Plan 1](../nurseops-now-state-bk7.html#plan-closing-the-gaps).

## Trade-offs

- A real count is an extra API call or a local tokenizer; a rough estimate is free but can be off.
- More levels give finer control but more paths to test.

## Interview answer

"I'd add token counting middleware in front of every model call: count the full request with the provider's API, compare it with the limit, and act at thresholds, dropping or summarizing old turns before anything is silently cut. Each call logs its level, so we can tune it."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
