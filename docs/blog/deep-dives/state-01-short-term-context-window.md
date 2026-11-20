# Deep dive 1 of 27: Three-Tier Memory: Short-Term (Context Window)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Context and State Management (Intro)](../nurseops-now-state.html#context-and-state-management-intro) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [Three-Tier Memory: Long-Term (Vector Store) →](state-02-long-term-vector-store.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Short-term memory is simply what the AI can see in this one call: its rules, the recent conversation, and the question. Nothing else exists for the model. Building that window well, every single time, is the first job of any AI assistant.

**In plain terms:** the papers on your desk right now; anything in the drawer might as well not exist until you take it out.

## The problem it solves

**LLMs are stateless**: the model forgets everything between calls, so the app must rebuild what it should know on every call. If it rebuilds too little, the AI forgets; too much, and it gets slow, costly and distracted.

**What the book proposes** (in my words): treat the context window as the short-term tier of memory: a small, deliberately assembled workspace, separate from long-term storage and the event log.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee chats with ServiceApps Assist about a VPN problem on ticket INC0012345. Each new question must be sent with the rules and only the recent turns.

**Steps.**

1. Keep the rules (system prompt) as a separate fixed text, not as the first chat message.
2. Store every turn, but send only the last N user + assistant pairs.
3. Add a one-line note about what the user is looking at (the ticket), not the whole ticket.
4. Put the new question last, so it gets the most attention.

**The code** (Python):

```python
SYSTEM = "You are ServiceApps Assist. Answer IT and HR questions from KB articles and the user's tickets. Cite KB numbers."
history = [("user", "My VPN keeps dropping"), ("assistant", "Which error code do you see? (KB0010234)"),
           ("user", "Error 809"), ("assistant", "809 means the VPN can't reach the server. Are you on guest Wi-Fi?"),
           ("user", "Yes, at a hotel"), ("assistant", "Turn off guest Wi-Fi or use your phone hotspot, then restart the client.")]
MAX_TURNS = 2   # send the last 2 user+assistant pairs

def build_window(history, question, ticket=None):
    recent = history[-2 * MAX_TURNS:]
    note = f"(The user is looking at ticket {ticket}.) " if ticket else ""
    return {"system": SYSTEM,
            "messages": [{"role": r, "content": t} for r, t in recent] + [{"role": "user", "content": note + question}]}

w = build_window(history, "Still failing on my hotspot", ticket="INC0012345")
print("system:", w["system"][:44] + "...")
for m in w["messages"]:
    print(f'{m["role"]:9s} {m["content"]}')
print(f"sent {len(w['messages'])} of {len(history) + 1} messages")
```

**Output** (from running the code above):

```
system: You are ServiceApps Assist. Answer IT and HR...
user      Error 809
assistant 809 means the VPN can't reach the server. Are you on guest Wi-Fi?
user      Yes, at a hotel
assistant Turn off guest Wi-Fi or use your phone hotspot, then restart the client.
user      (The user is looking at ticket INC0012345.) Still failing on my hotspot
sent 5 of 7 messages
```

**What to watch for.**

- Never let the rules become just another message that can be trimmed (see System Prompt Pinning).
- Count the window in tokens, not only turns, once messages can be long (see Token Counting Middleware).
- Facts that must be exact (ticket status, approvals) should be fetched, not remembered from chat.

**In plain terms:** the assistant only ever sees a clean desk: the rulebook, the last few messages and a sticky note saying which ticket you're on.
:::

## In NurseOps Now

Built. `claude_answer()` in `backend/app/services/assist.py` sends the rules in the API's `system` field, the last `ASSIST_TURNS` (10) turns, and a note like "(The user is looking at case 3.)". The demo in the parent post stored 12 turns and sent 10. See [Step 2](../nurseops-now-state.html#step-2-build-the-window).

## Trade-offs

- A small window is fast and cheap but can miss something said earlier; pair it with long-term memory.
- Turn limits are simple but blind to message length; token limits are precise but need a counter.

## Interview answer

"Short-term memory is just the context window, so I rebuild it on every call on purpose: the rules in the system field, only the last few turns, a one-line pointer to what the user is looking at, and the question last. Everything else lives outside and is fetched when needed."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
