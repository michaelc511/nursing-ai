# Deep dive 9 of 27: System Prompt Pinning

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state-bk7.html), section [Implementing Short-Term Memory: Token Budgets and Window Management (7.1)](../nurseops-now-state-bk7.html#implementing-short-term-memory-token-budgets-and-window-management-7-1) · [All 27 solutions](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives) · [← Dynamic Context Loading](state-08-dynamic-context-loading.html) · [Textual Summarization →](state-10-textual-summarization.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

System prompt pinning keeps the AI's rules in a protected place that is sent on every call and never trimmed. Only the conversation history slides. However long the chat gets, the rules are always there.

**In plain terms:** the company handbook is bolted to the desk; only the pile of notes next to it gets cleared out.

## The problem it solves

**Sliding window truncation** and **Loss of instructional integrity**: if the rules are just the first message, trimming old messages throws the rules away first.

**The standard approach** (in my words): split the context into an immutable zone (rules) that is never truncated and a mutable zone (history) that slides.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist's rule: never reset a password without identity verification. A chat reaches 10 turns and the window keeps only 6 messages.

**Steps.**

1. Keep the rules as a separate field (the API's system field), not in the message list.
2. Trim only the message list.
3. Re-send the rules unchanged on every call.
4. Test it: after a long chat, the rules must still be present.

**The code** (Python):

```python
RULES = "You are ServiceApps Assist. Never reset a password without identity verification. Cite KB numbers."

def naive_window(history, limit=6):              # rules are just the first message, so trimming drops them
    msgs = [{"role": "system", "content": RULES}] + history
    return msgs[-limit:]

def pinned_window(history, limit=6):             # rules kept apart; only history is trimmed
    return {"system": RULES, "messages": history[-limit:]}

history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"} for i in range(10)]
n, p = naive_window(history), pinned_window(history)
print("naive : rules present?", any(m["role"] == "system" for m in n), "| first message:", n[0]["content"])
print("pinned: rules present?", bool(p["system"]), "| first message:", p["messages"][0]["content"])
```

**Output** (from running the code above):

```
naive : rules present? False | first message: turn 4
pinned: rules present? True | first message: turn 4
```

**What to watch for.**

- Keep the pinned rules short; they're paid for on every call (prompt caching helps).
- Pinning keeps the rules present, not necessarily prominent; long chats may still need a reminder (see Recursive Goal Injection).
- Add a test that a long conversation still carries the rules.

**In plain terms:** the rulebook never leaves the desk, no matter how many notes pile up.
:::

## In NurseOps Now

Built. The rules (`backend/app/prompts/assist_v1.md`) go in the API's `system` field on every call, and only the history list is trimmed to 10 turns. See [Step 2](../nurseops-now-state-bk7.html#step-2-build-the-window).

## Trade-offs

- Pinned rules cost tokens on every call; cache them.
- Big rule sets crowd the window; keep them tight.

## Interview answer

"I never put the rules in the trimmable history. They go in the system field on every call, and only the conversation slides. That's the fix for the classic failure where a long chat pushes the policy out and the agent stops following it."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state-bk7.html#how-a-chat-turn-flows-and-where-state-lives)
