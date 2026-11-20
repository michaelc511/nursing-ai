# Deep dive 12 of 27: Entity Extraction

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (a different way)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Compression Strategies: Summarization and Entity Extraction (7.2)](../nurseops-now-state.html#compression-strategies-summarization-and-entity-extraction-7-2) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← Rolling Summaries](state-11-rolling-summaries.html) · [Vector Compression via RAG →](state-13-vector-compression-via-rag.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the book's problem, and its idea in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Entity extraction pulls the key facts out of a conversation (name, asset, issue, deadline, what was already tried) into a small structured record. That record is pinned at the top of the prompt, so the facts are never lost in summaries.

**In plain terms:** filling in the ticket's form fields instead of re-reading the whole email thread every time.

## The problem it solves

**History can't keep growing** and **Hallucination drift**: facts buried in a long chat get lost or changed when the chat is shortened.

**What the book proposes** (in my words): extract key variables into a structured JSON object that stays at the top of the context window, keeping facts exact while dropping the conversational scaffolding.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** An employee explains a VPN problem over four messages. ServiceApps Assist turns them into a profile.

**Steps.**

1. Define the fields you need (name, department, asset, issue, since, deadline, tried).
2. Ask the model to fill them as JSON with a schema (see Output Guardrails: Schema Enforcement).
3. Store the profile; update fields as new facts arrive.
4. Pin the profile at the top of each call instead of the old chat.

**The code** (Python):

```python
import json, re
chat = ["Hi, I'm Dana from Finance.", "Hello Dana! How can I help you today?",
        "My laptop LT-4471 won't connect to VPN since Monday.", "Sorry about that. Does it show an error code?",
        "No code, it just spins and then times out.", "Thanks. Have you tried restarting the laptop?",
        "I already restarted twice.", "Okay. Is this blocking your work right now?",
        "It's urgent, I have the quarter close on Friday.", "Understood, I'll treat this as high priority."]

def extract(lines):                              # stand-in for an AI call with a JSON schema
    text = " ".join(lines)
    return {"name": re.search(r"I'm (\w+)", text).group(1),
            "department": re.search(r"from (\w+)", text).group(1),
            "asset": re.search(r"\b[A-Z]{2}-\d{4}\b", text).group(0),
            "issue": "VPN won't connect, times out",
            "since": re.search(r"since (\w+)", text).group(1),
            "deadline": re.search(r"close on (\w+)", text).group(1),
            "already_tried": ["restart x2"]}

profile = extract(chat)
print(json.dumps(profile, indent=1))
print("pinned profile:", len(json.dumps(profile, separators=(",", ":"))), "chars, instead of the chat:", len(" ".join(chat)), "chars")
```

**Output** (from running the code above):

```
{
 "name": "Dana",
 "department": "Finance",
 "asset": "LT-4471",
 "issue": "VPN won't connect, times out",
 "since": "Monday",
 "deadline": "Friday",
 "already_tried": [
  "restart x2"
 ]
}
pinned profile: 163 chars, instead of the chat: 418 chars
```

**What to watch for.**

- Validate the extracted JSON with a schema; models invent fields or formats.
- Personal details in the profile must follow your privacy rules (see Sanitization layer).
- When a fact changes (a new deadline), overwrite it, don't append both.

**In plain terms:** the assistant keeps a small form filled in as you talk, and reads the form instead of the whole chat.
:::

## In NurseOps Now

Built, a different way. The AI review extracts the request's key fields (member, CPT code, ICD-10 codes, provider) into a validated JSON result stored in the `ai_reviews` table, and AI Assist fetches case facts with a tool instead of keeping a profile in the prompt. See [Step 4](../nurseops-now-state.html#step-4-hard-state-stays-in-sql).

## Trade-offs

- Exact and compact, but only for the fields you defined; anything else still needs the chat or a summary.
- Extraction is an AI call that can be wrong; validate it.

## Interview answer

"I extract the facts that matter into a typed record (asset, issue, deadline, what was tried) and pin that at the top of each call. The record is validated with a schema, and it survives any amount of chat compression because it's not chat."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
