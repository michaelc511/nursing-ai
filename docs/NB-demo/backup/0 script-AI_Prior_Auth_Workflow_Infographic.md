# Script: AI_Prior_Auth_Workflow_Infographic.png

Speaker script for the one-page NotebookLM infographic "AI Reads and Cites, Nurses Decide". Facts come from `docs/demo/2-talk-notes.md` and `docs/demo/1-short_script.md`.

**When to use it** (Claude's suggestion): either as a 3-minute overview at the start of the 10-minute intro, or as a 2-minute recap right before the 30-minute discussion, left on screen while people talk. It also works as a handout after the talk.

**Accuracy check:** everything on the infographic matches the docs. No fixes needed.

---

## Full walk-through (about 3 min)

### 1. Title: AI Reads and Cites, Nurses Decide (15 sec)

> "If you remember one thing from today, it's this line: AI reads and cites, nurses decide. This page shows how that works from start to finish."

### 2. The Problem, top left (30 sec)

> "Today a prior authorization takes 4.2 days on average. Nurses read every fax and PDF by hand, and 22% of requests come back for rework because something's missing. That load falls on the nurses."

### 3. Central Prior Auth Workflow, left to right (1 min 30 sec)

Point at each step as you go.

> "**Requests arrive.** Faxes, uploads and PDFs land in the intake inbox, just like today.
>
> **Cowork picks them up.** Claude Cowork runs a scheduled task called 'Prior auth intake'. It connects to our app through a connector called Prior Auth, which uses MCP, an open standard for giving AI a fixed set of tools.
>
> **Case creation.** Each PDF becomes a structured case: patient, procedure code, diagnosis code.
>
> **AI policy review.** Claude checks the request against the policy rules and cites the exact sentence and page for each one. Code then checks every quote against the PDF, and any mismatch sends the case to a person. It also flags missing paperwork right away and drafts the request to the provider.
>
> **Clinical decision.** This is where the AI stops. A nurse approves or pends. Only the medical director can deny."

### 4. Guardrails, top right (30 sec)

> "Three guardrails. The AI can't decide: Cowork has no tool to approve, pend or deny, and that's enforced in the service layer, not just hidden on the screen. Every Cowork action is logged under its own name, 'cowork', so the audit trail shows exactly what the AI did. And patient data is protected: personal details are removed from logs and traces, and this prototype uses synthetic data only."

### 5. Operational Value, bottom (30 sec)

> "The value. Intake happens in minutes, not days. Missing paperwork is caught on day one, which targets the 22% rework. And the run cost is low: about 10 cents per new case, nothing for an empty inbox, with hard caps of 50 cents per case and 10 dollars a day.
>
> The goal is 40% faster, from 4.2 days to about 2.5, with no added headcount. That's a goal; a pilot would measure it."

---

## Short version (about 1 min, for a recap)

> "Here's the whole thing on one page. Requests arrive by fax and upload. Claude Cowork picks them up on a schedule through the Prior Auth connector, turns each one into a case, and Claude checks it against the policy with exact citations, flagging anything missing on day one. Then people decide: nurses approve or pend, and only the medical director denies. Every Cowork action is logged as 'cowork', and the AI can't make a decision. The result: faster intake, earlier missing-paperwork alerts, about 10 cents a case. AI reads and cites; nurses decide."

---

## Questions this page invites

- *Does Cowork see patient data?* "Yes, it runs the review, so Claude reads the request. Personal details are kept out of logs and traces, and production would add HIPAA controls and a BAA. This prototype uses synthetic data only."
- *What if Cowork isn't running?* "The web app has a Check inbox button that runs the same services. Cowork is the operator, not the engine."
- *How fast is 'rapid intake'?* "A Cowork run of 3 requests takes about a minute and a half end to end."
