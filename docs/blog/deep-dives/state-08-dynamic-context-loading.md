# Deep dive 8 of 27: Dynamic Context Loading

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Implementing Short-Term Memory: Token Budgets and Window Management (7.1)](../nurseops-now-state-bk7.html#implementing-short-term-memory-token-budgets-and-window-management-7-1) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Token Counting Middleware](state-07-token-counting-middleware.html) · [System Prompt Pinning →](state-09-system-prompt-pinning.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Dynamic context loading means you don't paste everything the AI might need into the prompt. You give it a short note saying what's available and tools to fetch it, and it loads only what the current question needs.

**In plain terms:** a library card instead of carrying the whole library in your backpack.

## The problem it solves

**The token window is a hard limit** and **Loss of instructional integrity**: pasting a whole knowledge base or ticket history crowds out the rules and the question.

**The standard approach** (in my words): lazy-load: put a stub like "documentation available via the search tool" in the prompt and let the agent request specific sections.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** The company has 50 KB articles. An employee asks about VPN error 809 on a Mac.

**Steps.**

1. Replace pasted documents with a one-line stub naming the tools.
2. Give the model tools such as search_kb(question) and get_ticket(number).
3. Cap each tool result's size.
4. Let the model call tools as needed, up to a limit of rounds.

**The code** (Python):

```python
KB = {f"KB00{n}": f"Article {n} " + "text " * 400 for n in range(10000, 10050)}           # 50 articles
KB["KB0010234"] = "Connect to VPN on macOS. Error 809: the client can't reach the server; avoid guest Wi-Fi."
MAX_RESULT = 300

def search_kb(question, k=1):
    words = set(question.lower().split())
    ranked = sorted(KB.items(), key=lambda kv: -len(words & set(kv[1].lower().split())))
    return [(kid, text[:MAX_RESULT]) for kid, text in ranked[:k]]

STUB = "Knowledge base: available through the search_kb tool. Fetch only what you need."
all_chars = sum(len(t) for t in KB.values())
kid, text = search_kb("vpn error 809 on mac")[0]           # a real model decides to call the tool
print("whole KB if pasted:", all_chars, "chars")
print("stub in the prompt:", len(STUB), "chars")
print("fetched           :", kid, len(text), "chars ->", text)
```

**Output** (from running the code above):

```
whole KB if pasted: 100789 chars
stub in the prompt: 79 chars
fetched           : KB0010234 89 chars -> Connect to VPN on macOS. Error 809: the client can't reach the server; avoid guest Wi-Fi.
```

**What to watch for.**

- Cap tool results; one huge result can flood the window by itself.
- Limit tool rounds, so the agent can't loop forever.
- Treat fetched text as data, never as instructions.

**In plain terms:** the assistant knows where every article is and fetches one page when you ask, instead of reading you the whole manual.
:::

## In NurseOps Now

Built. AI Assist has read-only tools (`get_case`, `list_cases`, `stuck_cases`, `metrics`, `search_policy`, `search_guide`), each result capped at 12,000 characters, with at most 4 tool rounds (`assist.py`). See [Step 3](../nurseops-now-state-bk7.html#step-3-load-facts-only-when-needed).

## Trade-offs

- Tool calls add round trips and latency.
- The model may not fetch something it needed; good tool descriptions matter.

## Interview answer

"Instead of stuffing documents into the prompt, I give the model a short stub and tools to fetch what it needs, with size caps and a round limit. The window stays small and current, and every fact used has a source."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
