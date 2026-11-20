# Deep dive 26 of 27: Process Control: Self-Correction Loop

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (reviews)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Preventing Drift and Hallucinations in Long-Running Agents (7.4)](../nurseops-now-state.html#preventing-drift-and-hallucinations-in-long-running-agents-7-4) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Input Filtering: Relevance Pruning](state-25-input-filtering-relevance-pruning.html) · [Output Guardrails: Schema Enforcement →](state-27-schema-enforcement.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

A self-correction loop checks the AI's draft answer before the user sees it, and if a check fails, sends it back once with the exact failures to fix. Most mistakes get fixed on the second try; the rest are caught instead of shipped.

**In plain terms:** an editor who returns your draft with "this quote isn't in the source" circled, once, before it goes to print.

## The problem it solves

**Hallucination (The Grounding Failure)**: a first draft can contain a quote or fact that isn't in the source.

**What the book proposes** (in my words): ask the model to verify its answer against the provided context before returning the final result.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist's first draft misstates what VPN error 809 means; the check catches it and the retry fixes it.

**Steps.**

1. Generate a draft that includes its quotes.
2. Verify in code: every quote must appear in the source.
3. If it fails, retry once with the list of failures added to the prompt.
4. If it still fails, return MISSING_INFO and hand over to a person.

**The code** (Python):

```python
import re
SOURCE = "Error 809 means the VPN can't reach the server. Avoid guest Wi-Fi and restart the client."
attempts = iter(['Error 809 means your password expired. [quote: "your password expired"]',
                 'Error 809 means the VPN can\'t reach the server. [quote: "the VPN can\'t reach the server"]'])
def model(prompt): return next(attempts)         # stand-in for the AI call

def verify(draft):
    q = re.search(r'\[quote: "([^"]+)"\]', draft)
    return [] if q and q.group(1) in SOURCE else [f'quote not in source: "{q.group(1) if q else "none"}"']

def answer(question, max_retries=1):
    prompt = question
    for attempt in range(max_retries + 1):
        draft = model(prompt); fails = verify(draft)
        print(f"attempt {attempt + 1}: {'pass' if not fails else 'fail -> ' + fails[0]}")
        if not fails:
            return draft
        prompt = question + "\nYour previous answer failed these checks: " + "; ".join(fails) + ". Quote the source exactly."
    return "MISSING_INFO: couldn't verify an answer; a person will follow up."

print("final:", answer("What does VPN error 809 mean?"))
```

**Output** (from running the code above):

```
attempt 1: fail -> quote not in source: "your password expired"
attempt 2: pass
final: Error 809 means the VPN can't reach the server. [quote: "the VPN can't reach the server"]
```

**What to watch for.**

- Verify in code where you can; asking the same model "are you sure?" is weaker.
- Limit retries (one is usually enough) and cap cost per request.
- Send the specific failures back, not just "try again".

**In plain terms:** draft, check, fix once, and only then answer; if it still can't be verified, a person takes over.
:::

## In NurseOps Now

Built for case reviews: `review_graph.py` runs `ai_review → verify`; a failed quote check sends Claude back once with the failures, unless the case's cost cap is reached. Tests: `test_failed_quote_retries_claude_once_with_feedback`, `test_no_retry_when_quotes_verify`. See [Step 11](../nurseops-now-state.html#step-11-ground-every-answer).

## Trade-offs

- Each retry costs another AI call and adds latency.
- Code checks only catch what they test (quotes, formats), not every wrong fact.

## Interview answer

"Drafts go through a verify step in code, for example every quote must be in the source. On failure the model gets one retry with the exact failures listed, and if it still fails we return MISSING_INFO and hand off to a person. It fixes most errors and never ships an unverified one."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
