# 15-minute prototype: build NurseOps' core live with Claude Code

Use this if the interviewer says **"build me a prototype in 15 minutes."** You build it by pasting the
prompts below into Claude Code; each step runs before the next one starts.

Paste the prompts as they are. Claude Code recognizes them as build requests even in interview mode,
builds, and then goes back to answering as you.

---

## 0. What to say first (30 s)

> "Sure. In 15 minutes I'll build the core of NurseOps: Claude reads a prior auth request and the coverage
> policy, returns a structured review with page-and-quote citations, and code checks every quote. It never
> approves or denies; that stays with a nurse. Then I'll expose it as an MCP tool so Claude Cowork can run
> it. I'll build it with Claude Code, the way I built the real one."

## Timeline

| Min | Step | Prompt |
|---|---|---|
| 0–1 | Say the scope (above) | none |
| 1–6 | **Step 1:** review script, mock mode | P1 |
| 6–8 | **Step 2:** quote check, show a fake quote failing | P2 |
| 8–10 | **Step 3:** run on real Claude (optional, ~$0.10) | P3 |
| 10–13 | **Step 4:** MCP server for Cowork | P4 |
| 13–15 | **Step 5:** Cowork calls it, or the Prior Auth fallback | P5 |

If time runs short, stop after Step 2 and *describe* Steps 4–5 ("here's how it plugs into Cowork"), then
show the real thing with the **Prior Auth** connector.

## What's already on this Mac (checked 2026-11-17)
- Python: `nursing-ai/backend/venv` has `anthropic` 2.8, `pydantic`, `pypdf`, `mcp` 1.30. No installs needed.
- Request PDFs: `nursing-ai/data/samples/72148_a_complete.pdf` (lumbar, complete),
  `73721_b_missing_pt.pdf` (knee, missing PT notes), `70551_c_not_met.pdf` (brain, criteria not met).
- Policy PDFs: `nursing-ai/backend/policies/72148.pdf`, `73721.pdf`, `70551.pdf`.
- `fly` installed. **Not installed:** `cloudflared` / `ngrok` (needed only for Step 5 with a new connector).

**Before the interview (5 min):** `brew install cloudflared`, and have the Prior Auth connector working in
Cowork as the fallback.

---

## Step 1: the review script (P1)

```
Build a 15-min prototype in nursing-ai/quick-proto/ (new folder, don't touch the main app).
One file review.py, under 100 lines, run with nursing-ai/backend/venv/bin/python:
- input: a request PDF path; read its CPT code with a regex, pick backend/policies/<cpt>.pdf
- send both PDFs to Claude (anthropic SDK, native PDF documents, model from CLAUDE_MODEL env,
  default claude-opus-5-5) with a short prompt in quick-proto/prompt.md:
  never approve or deny, cite page + exact quote for every claim
- output validated by a Pydantic model Review: fields (member, cpt, icd10, provider), missing[],
  criteria[] {criterion, result met|not_met|unclear, quote, page}, tier likely_approve|needs_review|
  likely_deny, summary, draft_provider_request
- MOCK=1 (default when ANTHROPIC_API_KEY is unset) returns a fixed Review for the sample so it runs offline
- print the review as a readable table
Run it in mock mode on data/samples/73721_b_missing_pt.pdf and show me the output.
```

**Expected:** a table with the knee case, the missing PT notes, criteria with page + quote, tier.
**Say while it runs:** "The schema is the contract between the AI and the code. If Claude returns anything
that doesn't fit, it's rejected, not shown to a nurse."

## Step 2: verify the quotes (P2)

```
In review.py add verify(): extract text per page from the request and policy PDFs with pypdf,
normalize case, whitespace and curly quotes, and check each quote appears on the page it cites. Mark each
criterion verified true/false; any failure adds a warning and forces tier = needs_review. Then run it twice
on the knee sample: once normally, once with one quote deliberately changed (--fake-quote flag), and show
both results side by side.
```

**Expected:** run 1 all ✓; run 2 one ✗, a warning, tier forced to needs_review.
**Say:** "I don't trust the model's citations; I check them. A quote that isn't on that page sends the case
to a person. That's the core safety idea of NurseOps."

## Step 3: real Claude (P3, optional, ~$0.10)

Only if `ANTHROPIC_API_KEY` is set in your shell. Never paste the key into the chat.

```
Run review.py on real Claude (MOCK=0) on data/samples/72148_a_complete.pdf. Show the table,
the verified ticks, tokens and cost for the call.
```

**Say:** "Same code, real model. Notice the tier is a suggestion; there's no field for a decision at all."

## Step 4: MCP server for Cowork (P4)

```
Add quick-proto/mcp_server.py with FastMCP (mcp 1.30): tools review_case(pdf_name) that runs
review.py's pipeline on a file in data/samples, and list_samples(). No approve or deny tool. Keep a tiny
in-memory log of reviews with timestamp and actor "cowork". Serve Streamable HTTP on port 8765 at /mcp.
For this demo set transport_security with allowed_hosts ["localhost:*", "127.0.0.1:*", "*.trycloudflare.com"].
Show me the command to start it, then test it with a local MCP client call to list_samples and review_case.
```

**Expected:** tool list prints 2 tools; a review comes back through MCP.
**Say:** "Two tools, both read or prepare. There's no decide tool, so Cowork can't approve or deny. In the
real app MCP calls the same service layer as the web UI, so every rule applies to it."

## Step 5: Cowork calls it (P5)

**You** run these (Mike runs apps himself), each in its own Terminal tab:

```
cd ~/projects/nursing-ai && backend/venv/bin/python quick-proto/mcp_server.py
cloudflared tunnel --url http://localhost:8765
```

1. Copy the `https://<random>.trycloudflare.com` address cloudflared prints.
2. In Claude: **Customize → Connectors → Add → Add custom connector**. Name `Quick Proto`, URL
   `https://<random>.trycloudflare.com/mcp`. No token (demo only, synthetic data, URL dies when you stop it).
3. In Cowork: *"Use the Quick Proto connector. List the samples, review the knee MRI request, and tell me
   what's missing and the suggested tier. Don't approve or deny."*

**Say:** "Cowork is the operator, not the engine. It called my tool through MCP and reported back. In the real
app this runs on a schedule, and it's deployed with a token instead of a temporary tunnel."

**After the interview:** stop both commands and remove the Quick Proto connector.

### Fallback (any Step 5 problem)
Open Cowork with the **Prior Auth** connector (the real app on Fly) and run:
*"Use the Prior Auth connector. What cases are ready for review, by tier, and which are incomplete?"*
**Say:** "Here's the full version of the same pattern, already deployed: 7 tools, token-protected, no decide tool."

---

## Change requests they might make (paste as-is)
- `Add a field for the ordering physician and urgency (Standard/Expedited) and rerun.`
- `Add a criterion: conservative therapy at least 6 weeks. Rerun on the lumbar sample.`
- `Run it on the brain MRI sample and explain the tier.`
- `Add a stuck_cases tool to the MCP server.`
- `Add an audit line per review: who, when, tier, prompt version.`
- `Show the prompt.md and explain each rule in one line each, as me.`

## Explaining while it builds
- `Give me 3 sentences to say right now about what you're building, as me.`
- `Walk me through review.py top to bottom in 30 seconds, as me.`
- `How does this prototype become NurseOps? 30 seconds, as me.`

## If something breaks
| Problem | Paste |
|---|---|
| Any error | `It failed with: <paste error>. Fix it fast and rerun.` |
| No API key | `Use mock mode and rerun.` |
| Need a line while fixing | `One sentence to say while you fix this, as me.` |
| MCP 421 / host not allowed | `The tunnel host is rejected; fix allowed_hosts and restart instructions.` |
| Connector won't add / Cowork can't reach it | Use the **Fallback** above. |
| Running out of time | Stop, say: "Here's where it goes next", and use the wrap-up prompt below. |

## Wrap-up (30 s)
```
30 seconds, as me: what I'd add next to turn this into NurseOps (state machine, human decisions,
audit log, RAG over policies, evals, deploy with a token).
```

> "That's the core in 15 minutes: Claude reads and cites, code verifies, Cowork operates, and a person
> decides. The full NurseOps adds the case state machine with human-only decisions, an audit trail, hybrid
> policy search, an eval gate and a token-protected deploy, all on the same pattern."

