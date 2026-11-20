# Deep dive 20 of 27: Sanitization layer

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← The Rehydration Pattern](state-19-rehydration-pattern.html) · [TTL (time-to-live) expiration →](state-21-ttl-expiration.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

A sanitization layer masks personal data and secrets before anything is saved: chat memory, logs, traces, vector stores. Saved state outlives the conversation, so whatever goes in can leak later.

**In plain terms:** blacking out names and account numbers before a document goes into the archive.

## The problem it solves

**Persistence creates liability**: if memory or logs store emails, phone numbers, passwords or API keys, you've built a data leak.

**What the book proposes** (in my words): always implement a sanitization layer that scrubs secrets and personal data before writing state to disk.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee pastes their email, phone, a password and an API key into a ServiceApps Assist chat.

**Steps.**

1. List the patterns to mask (emails, phones, IDs, passwords, API keys) plus known names.
2. Run every text through `redact()` before saving to memory.
3. Add a logging filter, so logs are masked automatically.
4. Test it with fake data, like the example below.

**The code** (Python):

```python
import re, logging, io
PATTERNS = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
            (re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"), "[PHONE]"),
            (re.compile(r"\b(sk|pk|api)[-_][A-Za-z0-9]{16,}\b"), "[SECRET]"),
            (re.compile(r"(?i)password\s*[:=]\s*\S+"), "password: [SECRET]"),
            (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]")]
def redact(t):
    for rx, rep in PATTERNS:
        t = rx.sub(rep, t)
    return t

class RedactingFilter(logging.Filter):
    def filter(self, record):
        record.msg, record.args = redact(record.getMessage()), ()
        return True

buf = io.StringIO()
log = logging.getLogger("assist"); h = logging.StreamHandler(buf); h.addFilter(RedactingFilter())
log.addHandler(h); log.setLevel(logging.INFO)
msg = "I'm dana@example.com, 555-201-3344, password: Hunter2! and my key is sk_live1234567890abcdefXYZ"
log.info("question=%s", msg)
print("logged:", buf.getvalue().strip())
print("saved :", redact(msg))
```

**Output** (from running the code above):

```
logged: question=I'm [EMAIL], [PHONE], password: [SECRET] and my key is [SECRET]
saved : I'm [EMAIL], [PHONE], password: [SECRET] and my key is [SECRET]
```

**What to watch for.**

- Pattern masking misses unusual formats; add exact-name masking for known people.
- Mask before the data reaches any third-party tracing or analytics tool.
- Keep the original only where it's truly needed, with access control.

**In plain terms:** every note is run through a black marker before it's filed.
:::

## In NurseOps Now

Built: `backend/app/pii.py` masks SSNs, dates, emails, phones, member IDs, NPI numbers, addresses and the case's member and provider names before chat memory is saved; a logging filter masks logs; LangSmith gets a masked thread ID. The parent post's demo showed DOB, phone and SSN masked. See [Step 6](../nurseops-now-state.html#step-6-mask-then-save-the-turn).

## Trade-offs

- Masking can remove something useful (a phone number the user wanted noted).
- Regex is fast but imperfect; NER models catch more but cost more.

## Interview answer

"Everything persisted, from memory to logs to traces, goes through a sanitization layer first: pattern masking for emails, phones, IDs and keys, plus exact-name masking for known people, and a logging filter so nobody can forget. Saved state outlives the chat, so that's where leaks happen."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
