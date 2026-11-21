# Deep dive 24 of 27: Engineering Fix: Strict RAG and Citation Enforcement

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Preventing Drift and Hallucinations in Long-Running Agents (7.4)](../nurseops-now-state.html#preventing-drift-and-hallucinations-in-long-running-agents-7-4) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Engineering Fix: Recursive Goal Injection](state-23-recursive-goal-injection.html) · [Input Filtering: Relevance Pruning →](state-25-input-filtering-relevance-pruning.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Strict RAG means the AI may only answer factual questions from retrieved sources, and must cite them. If the source isn't there, it says so ("MISSING_INFO") instead of guessing. A check then confirms every quote really appears in its source.

**In plain terms:** no claim without a page number, and someone checks the page.

## The problem it solves

**Hallucination (The Grounding Failure)**: when the answer isn't in the context, the model fills the gap with something plausible and wrong.

**The standard approach** (in my words): the agent can't answer factual questions unless it cites a retrieved chunk; otherwise it outputs a predefined marker such as MISSING_INFO.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist answers four questions; some answers cite correctly, one misquotes, one cites nothing, one honestly says it can't find the information.

**Steps.**

1. Tell the model: answer only from the retrieved chunks, cite them as [ID] "quote", else say MISSING_INFO.
2. After the answer, check each citation: the source exists and the quote is in it.
3. Block or flag answers that fail.
4. Count MISSING_INFO answers; they show gaps in the knowledge base.

**The code** (Python):

```python
import re
CHUNKS = {"KB0010234#errors": "Error 809 means the VPN can't reach the server. Avoid guest Wi-Fi and restart the client.",
          "KB0020311#4": "Employees may work from another country for up to 10 working days a year."}

def check(answer):
    if answer.startswith("MISSING_INFO"):
        return "OK (honest MISSING_INFO)"
    m = re.search(r'\[(KB\d+#\w+)\]\s*"([^"]+)"', answer)
    if not m:
        return "BLOCKED: no citation"
    cid, quote = m.groups()
    if cid not in CHUNKS:
        return f"BLOCKED: unknown source {cid}"
    if quote not in CHUNKS[cid]:
        return f"BLOCKED: quote not in {cid}"
    return "OK"

answers = ['Avoid guest Wi-Fi. [KB0010234#errors] "Avoid guest Wi-Fi and restart the client."',
           'You can work abroad for 30 days. [KB0020311#4] "up to 30 working days a year"',
           'Your laptop is probably fine.',
           "MISSING_INFO: I can't find your laptop's warranty in the knowledge base."]
for a in answers:
    print(f"{check(a):28s} <- {a[:58]}")
```

**Output** (from running the code above):

```
OK                           <- Avoid guest Wi-Fi. [KB0010234#errors] "Avoid guest Wi-Fi a
BLOCKED: quote not in KB0020311#4 <- You can work abroad for 30 days. [KB0020311#4] "up to 30 w
BLOCKED: no citation         <- Your laptop is probably fine.
OK (honest MISSING_INFO)     <- MISSING_INFO: I can't find your laptop's warranty in the k
```

**What to watch for.**

- Check quotes in code; don't trust the model's own claim that it cited.
- Allow honest "I don't know" answers; punishing them encourages guessing.
- Quote checks need exact text; normalize spaces and punctuation consistently.

**In plain terms:** every answer must point to the KB line it came from, and a checker reads that line to confirm.
:::

## In NurseOps Now

Built: AI Assist's prompt says answer only from tools and say "I don't know" otherwise; the `check` node adds a "please check" note to answers without sources; and every case review quote must match the PDF exactly, or the review is sent back once. See [Step 11](../nurseops-now-state.html#step-11-ground-every-answer).

## Trade-offs

- More "I don't know" answers, which is the honest cost of fewer made-up ones.
- Exact quote checks can fail on harmless formatting differences.

## Interview answer

"Factual answers must cite a retrieved chunk with an exact quote, and code checks that the quote is really in that chunk. No source means an explicit MISSING_INFO, not a guess. That turns hallucination from a silent failure into a visible, countable one."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
