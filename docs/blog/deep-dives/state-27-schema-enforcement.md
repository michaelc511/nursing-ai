# Deep dive 27 of 27: Output Guardrails: Schema Enforcement

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Preventing Drift and Hallucinations in Long-Running Agents (7.4)](../nurseops-now-state.html#preventing-drift-and-hallucinations-in-long-running-agents-7-4) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Process Control: Self-Correction Loop](state-26-self-correction-loop.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Schema enforcement requires the AI's answer to match a fixed structure: specific fields, types and allowed values. Code validates it; if it doesn't fit, it's rejected or retried. Downstream code can then trust the shape of every answer.

**In plain terms:** a form with drop-down menus: you can't type "urgent!!" where the form needs a priority from 1 to 4.

## The problem it solves

**Hallucination (The Grounding Failure)**: free-form answers can invent fields, values or formats that break the code that uses them.

**What the book proposes** (in my words): use libraries like Pydantic or Instructor to force the output into a strict structure, and retry when validation fails.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist triages tickets into category, priority, KB articles and a reply. Three model outputs are validated.

**Steps.**

1. Define the schema: allowed categories, a priority range, a KB number format, reply length.
2. Ask the model for JSON in that schema (many APIs can enforce it directly).
3. Validate in code; reject or retry on failure.
4. Remember: a valid shape isn't a true answer; still check the facts.

**The code** (Python):

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ValidationError, StringConstraints

KBNumber = Annotated[str, StringConstraints(pattern=r"^KB\d{7}$")]
class TicketTriage(BaseModel):
    category: Literal["network", "hardware", "software", "access", "hr"]
    priority: int = Field(ge=1, le=4)
    kb_articles: list[KBNumber]
    reply: str = Field(min_length=10, max_length=400)

outputs = ['{"category": "network", "priority": 2, "kb_articles": ["KB0010234"], "reply": "Avoid guest Wi-Fi and restart the VPN client."}',
           '{"category": "urgent!!", "priority": 9, "kb_articles": ["see the VPN doc"], "reply": "ok"}',
           'Sure! The category is network and the priority is high.']
for raw in outputs:
    try:
        t = TicketTriage.model_validate_json(raw)
        print("VALID   ", t.category, t.priority, t.kb_articles)
    except ValidationError as e:
        print("INVALID ", e.error_count(), "errors in:", [str(er["loc"][0]) if er["loc"] else "json" for er in e.errors()])
```

**Output** (from running the code above):

```
VALID    network 2 ['KB0010234']
INVALID  4 errors in: ['category', 'priority', 'kb_articles', 'reply']
INVALID  1 errors in: ['json']
```

**What to watch for.**

- A schema guarantees shape, not truth; pair it with source checks.
- Prefer the API's built-in structured output over parsing free text.
- Keep allowed values in one place, shared by the schema and the code.

**In plain terms:** the assistant must fill in a strict form; anything that doesn't fit the boxes is sent back.
:::

## In NurseOps Now

Built: every case review must match the `ReviewResult` Pydantic schema, requested through the Anthropic SDK's structured output (`messages.parse`) in `backend/app/llm/client.py`; a refusal or unparseable answer falls back to the backup model or returns "AI unavailable". See [Step 11](../nurseops-now-state.html#step-11-ground-every-answer).

## Trade-offs

- Strict schemas make code simple and safe, but can push the model into filling fields it isn't sure about; allow "unclear".
- Schema changes need prompt and code changes together.

## Interview answer

"Every structured answer is validated against a Pydantic schema with allowed values and formats, ideally enforced by the API's structured output, with a retry on failure. It makes the output safe for code, and I'm explicit that it guarantees shape, not truth; grounding checks handle truth."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
