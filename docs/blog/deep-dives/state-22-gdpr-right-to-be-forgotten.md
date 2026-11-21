# Deep dive 22 of 27: GDPR Right to Be Forgotten

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: 🟡 partly built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← TTL (time-to-live) expiration](state-21-ttl-expiration.html) · [Engineering Fix: Recursive Goal Injection →](state-23-recursive-goal-injection.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Under GDPR, a person can ask for their personal data to be deleted. For an AI assistant, that means finding and erasing that person's data in every store (chat memory, profiles, vector memory, logs) and proving it was done.

**In plain terms:** when a customer leaves and asks to be forgotten, you shred every copy of their file, not just the one on your desk.

## The problem it solves

**Persistence creates liability**: memories spread across many stores, and forgetting one person means finding them all.

**The standard approach** (in my words): make sure the persistence layer complies with regulations like GDPR's right to be forgotten.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** Employee u42 leaves the company and asks for their assistant data to be erased.

**Steps.**

1. Keep a map of every store that can hold user data.
2. Tag every saved item with the user ID, so it can be found.
3. Erase per store, then verify nothing is left.
4. Record the erasure in an audit row without personal data.

**The code** (Python):

```python
stores = {"chat_memory": {"u42:INC0012345": ["..."], "u42:general": ["..."], "u77:general": ["..."]},
          "profiles": {"u42": {"contact": "email"}, "u77": {"contact": "phone"}},
          "vector_memory": [{"user": "u42", "text": "asset LT-4471"}, {"user": "u77", "text": "Berlin office"}],
          "logs": ["u42 asked about VPN", "u77 asked about leave"]}
audit = []

def forget(user):
    n = 0
    for k in [k for k in stores["chat_memory"] if k.startswith(user + ":")]:
        del stores["chat_memory"][k]; n += 1
    n += stores["profiles"].pop(user, None) is not None
    before = len(stores["vector_memory"])
    stores["vector_memory"] = [d for d in stores["vector_memory"] if d["user"] != user]
    n += before - len(stores["vector_memory"])
    before = len(stores["logs"])
    stores["logs"] = [l for l in stores["logs"] if not l.startswith(user + " ")]
    n += before - len(stores["logs"])
    audit.append({"action": "erase_user", "items": n})        # no personal data in the audit row
    return n

print("erased items:", forget("u42"))
print("anything left for u42?", any("u42" in str(v) for v in stores.values()))
print("u77 untouched:", list(stores["chat_memory"]), stores["profiles"])
print("audit:", audit)
```

**Output** (from running the code above):

```
erased items: 5
anything left for u42? False
u77 untouched: ['u77:general'] {'u77': {'contact': 'phone'}}
audit: [{'action': 'erase_user', 'items': 5}]
```

**What to watch for.**

- Don't forget backups, caches, traces and third-party tools.
- Some records (financial, legal) may have to be kept; document the exceptions.
- Verify after erasing; deletion bugs are silent.

**In plain terms:** one button that finds the person in every drawer, shreds each copy, and logs that it happened.
:::

## In NurseOps Now

Partly built: "Clear" deletes one AI Assist thread and writes an audit row (the parent post's demo). There's no single "erase everything for this user" across all stores. See [Step 9](../nurseops-now-state.html#step-9-forget-on-request).

## Trade-offs

- Tagging everything with a user ID is design work upfront, but it's the only way erasure can be complete.
- Erasure conflicts with audit needs; keep audit rows free of personal data.

## Interview answer

"To honor a deletion request, every store that can hold user data is tagged by user ID and listed, so one job can erase the person everywhere, verify nothing remains, and write an audit row with no personal data. Most failures here are a forgotten copy, like a cache or a trace."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
