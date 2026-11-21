# Deep dive 21 of 27: TTL (time-to-live) expiration

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ⬜ not built (illustrative)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Sanitization layer](state-20-sanitization-layer.html) · [GDPR Right to Be Forgotten →](state-22-gdpr-right-to-be-forgotten.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

TTL expiration gives every saved item an expiry date and deletes it automatically when it passes. Old chat memory and personal data don't pile up forever.

**In plain terms:** milk with a sell-by date: after it, it goes, without anyone having to remember.

## The problem it solves

**Persistence creates liability**: data kept forever is a growing privacy and security risk, and old memories can mislead the AI.

**The standard approach** (in my words): consider automatic TTL expiration on sensitive data.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist keeps chat memory for 90 days. A nightly job deletes expired threads and logs each deletion.

**Steps.**

1. Store an `expires` date with each saved item (saved date + TTL).
2. Run a scheduled job that deletes expired items.
3. Write an audit row for each deletion (without the deleted content).
4. Choose TTLs per data type (chat 90 days, audit logs longer, per policy).

**The code** (Python):

```python
import sqlite3, datetime as dt
db = sqlite3.connect(":memory:")
db.execute("create table memory(thread text, saved date, expires date, text text)")
db.execute("create table audit(at date, action text, thread text)")
TTL_DAYS = 90

def save(thread, text, today):
    exp = (dt.date.fromisoformat(today) + dt.timedelta(days=TTL_DAYS)).isoformat()
    db.execute("insert into memory values(?,?,?,?)", (thread, today, exp, text))

def purge(today):                                # the nightly job
    gone = [r[0] for r in db.execute("select distinct thread from memory where expires < ?", (today,))]
    db.execute("delete from memory where expires < ?", (today,))
    for t in gone:
        db.execute("insert into audit values(?,?,?)", (today, "ttl_purge", t))
    return gone

save("u42:INC0010001", "printer chat", "2026-07-01")
save("u42:INC0012345", "vpn chat", "2026-11-18")
save("u77:general", "hr question", "2026-08-25")
print("purged on 2026-11-19:", purge("2026-11-19"))
print("left:", [r[0] for r in db.execute("select thread from memory")])
print("audit:", db.execute("select * from audit").fetchall())
```

**Output** (from running the code above):

```
purged on 2026-11-19: ['u42:INC0010001']
left: ['u42:INC0012345', 'u77:general']
audit: [('2026-11-19', 'ttl_purge', 'u42:INC0010001')]
```

**What to watch for.**

- Expire copies too: backups, caches, vector stores.
- Audit the deletion, not the content.
- Legal holds may require keeping some data; make TTL configurable per type.

**In plain terms:** every saved chat has a delete-by date, and a nightly cleaner removes the expired ones and notes it in the log.
:::

## In NurseOps Now

Not built: AI Assist threads are kept until a user clears them. Capping and expiring memory is [Plan 3](../nurseops-now-state.html#plan-closing-the-gaps). See [Step 9](../nurseops-now-state.html#step-9-forget-on-request).

## Trade-offs

- Less risk and less storage, but the AI forgets older context.
- Another scheduled job to run and monitor.

## Interview answer

"Saved memory gets an expiry date per data type, and a nightly job deletes what's expired and writes an audit row without the content. It keeps the privacy risk from growing silently and keeps old, stale memories out of the AI's context."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
