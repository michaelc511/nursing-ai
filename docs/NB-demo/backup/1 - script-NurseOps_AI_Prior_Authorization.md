# Script: NurseOps_AI_Prior_Authorization.pdf

Speaker script for the 15-slide NotebookLM deck (light blue design, starts "NurseOps Now: AI for Faster Prior Authorization, Run by Claude Cowork"). 45 minutes, focus on Claude Cowork.

Facts come from `docs/demo/2-talk-notes.md`, `docs/demo/1-short_script.md` and `docs/demo/4-demo-script.md`. The timing split below is Claude's suggestion, built around your 10-minute intro and 30-minute discussion.

| Part | Slides | Time |
| --- | --- | --- |
| 1. Intro | 1–5 | 10 min |
| 2. Claude Cowork: live demo and discussion | 6–13 (live demo after slide 8) | 30 min |
| 3. Close and questions | 14–15 | 5 min |

**Fix on the slides, or correct them out loud** (the deck says something the docs don't support):
- Slide 7 names 4 tools. Cowork actually has **7**: run_all, poll_intake, review_case, get_cases, get_case, get_stuck_cases, get_metrics.
- Slide 6 says Cowork wakes "every 15 minutes". Today you run the task on demand or daily; every 15 minutes is the production plan.
- Slide 8 says "no data leaves the server". OCR and embeddings run locally, but the request PDF **is** sent to Claude through the API. In production that's covered by a BAA.
- Slide 11 says "zero hallucination tolerance". The accurate claim: code checks every quote, and a mismatch forces a person to review it.

---

## Part 1: Intro (10 min)

### Slide 1: NurseOps Now, AI for Faster Prior Authorization, Run by Claude Cowork (1 min)

**Before you start:** the status bar on this slide is your checklist. The live app is awake, you're logged in as `nurse1`, `meddir` is open in a private window, and the Prior Auth connector is on in Cowork.

> "Good morning. I'm Mike Chang. Today I'll show you NurseOps Now, an AI prototype that helps nurses move prior authorization requests faster. It's live on the web right now, it runs on Claude, and it's operated by Claude Cowork. Everything you'll see uses synthetic data, so there are no real patients.
>
> The plan for the next 45 minutes: about 10 minutes on the problem and the idea, then most of our time on Cowork, with a live demo and an open discussion, and a few minutes for questions at the end."

### Slide 2: The 4.2-Day Waiting Game (2 min)

> "Here's the problem. A regional health plan gets about 15,000 prior authorization requests a month. They arrive by fax, PDF, portal and provider upload, and a nurse reads every one by hand.
>
> On average a request waits 4.2 days. Most of that is the pile on the left: days one to three, waiting in a queue. On day four a nurse finally opens a 10-page request and checks it against a 5-page policy.
>
> And 22% of the time she finds something missing, like physical therapy notes. Now the clock starts over, the provider gets a late request, and the provider calls to ask where things stand. That's the cost: nurses doing data entry, patients waiting for care, and staff chasing paperwork."

### Slide 3: A 40% Faster Target, Zero Extra Headcount (2 min)

> "The goal is to cut turnaround by 40%, from 4.2 days to about 2.5, without adding staff and without lowering clinical quality or compliance.
>
> I want to be clear: 40% is a goal. We haven't measured it on real work yet, and that's what a pilot would do.
>
> The idea: on the left, every format lands on the nurse. On the right, AI reads each request the moment it arrives and prepares the case, so the nurse spends her time on clinical judgment, not typing.
>
> Under the hood it's a Python service layer with FastAPI, a React web app, and a database, deployed live on Fly.io."

### Slide 4: Three Ways AI Transforms the Queue (3 min)

> "There are three places where AI helps.
>
> **One: catch missing information right away.** Claude reads each request as it arrives, pulls out the patient, the procedure code and the diagnosis code, and flags anything missing. It also drafts the note to the provider. So rework starts on day one, not day four. That targets the 22%.
>
> **Two: a copilot for the nurse.** Claude compares the documents to the policy criteria. Every claim cites a page and a quote, and it suggests a tier: likely approve, needs review, or likely deny. It's a suggestion. The nurse decides.
>
> **Three: visibility.** Leaders and staff can ask in plain English, 'What's stuck?' or 'What's our override rate?', and get an answer from live data. That cuts the status calls.
>
> All three run on Claude with a structured, validated output, and the policy search uses retrieval with re-ranking, so Claude sees the right clause."

### Slide 5: AI Reads & Cites. Nurses Decide. (2 min)

> "This is the one rule that never changes. AI reads and cites; people decide.
>
> Lane one: AI and Cowork read the PDFs, check the policy, highlight what's missing and suggest a tier. They have zero authority to approve or deny.
>
> Lane two: the nurse reviews the citations and can approve or pend. If she disagrees with the AI, that's recorded as an override. Nurses can't deny.
>
> Lane three: only the medical director can deny.
>
> And this isn't just hidden buttons on a screen. It's enforced in the service layer, so no screen, no tool and no automation can get around it.
>
> Now let's talk about the part that runs all of this: Claude Cowork."

---

## Part 2: Claude Cowork, live demo and discussion (30 min)

### Slide 6: Meet Your 24/7 Shift Supervisor (3 min)

> "Think of Cowork as a shift supervisor for the intake queue. Cowork is Claude in the desktop app, connected to our system.
>
> We gave it a scheduled task called 'Prior auth intake'. When it runs, it calls one tool, run all, which takes in every new request, turns each PDF into a case, and has Claude review it against the policy.
>
> Then it writes a report, like the one on the slide: 3 new cases, 1 missing paperwork, 1 that looks good, 1 that needs review, and all of them waiting on nurses.
>
> For this demo I run it on demand. In production it would run every 15 minutes or whenever a new request arrives.
>
> The key line: Cowork is the operator, not the engine. If you replace Cowork with a plain scheduler, nothing else changes. Cowork adds the plain-English report and the ability to ask questions."

### Slide 7: Securely Plugged In, Strictly Limited (3 min)

> "How does Cowork connect? Through MCP, the Model Context Protocol. It's an open standard for giving AI a set of tools. Our app exposes it at a secure address, protected by a token, and in Cowork it shows up as a connector called 'Prior Auth'.
>
> Cowork gets 7 tools: take in requests, review a case, list cases, look at one case, find stuck cases, and get metrics. Run all combines intake and review.
>
> Look at what's missing: there is no approve tool and no deny tool. That's not a setting we could forget to turn on; the tool doesn't exist.
>
> And MCP isn't a back door. It calls the same service layer as the web app, so every rule and every log applies to Cowork exactly as it does to a nurse."

### Slide 8: Automating the Triage Phase (2 min)

> "Here's the flow you're about to see live. A new request lands in the inbox. Cowork runs. Each request becomes a case: code reads the procedure code, Claude reviews it, code checks Claude's quotes, and the case is flagged complete or incomplete. Nurses see a queue that's already sorted and prepared.
>
> One accuracy note: scanned pages are read with OCR on our own server, but the request itself does go to Claude through the API. In production that's covered by a business associate agreement.
>
> Let's run it."

### Live demo (about 12 min)

Matches the 8 recorded clips in `docs/demo/video-demo/0 Video Script.html`. If a step fails live, play its clip from `docs/demo/video-demo/`.

**Before you start:** the app is awake and `nurse1` is signed in; a private window is open on the login screen for `meddir`; Cowork (the Claude app) is open with **Prior Auth** turned on; Terminal is ready with the step 2 commands.

Step 1: **Web app: the current queue (`nurse1`).** Show the queue. Point at the metric tiles, the **Last run · Cowork preview** card, and the existing cases with their tiers. (Clip: `1 Web App.mov`)

> "This is the nurse's queue. These tiles are our success metrics: turnaround, rework rate, cases reviewed and how often nurses override the AI. Let's bring in new requests."

Step 2: **New requests arrive (Terminal).** Wake the app and wait for `200`:

```
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" https://nurseops-now.fly.dev/api/health
```

Copy the 3 requests into the inbox (works from any folder):

```
fly ssh console --app nurseops-now -C "cp /app/data/samples/72148_a_complete.pdf /app/data/samples/73721_b_missing_pt.pdf /app/data/samples/70551_c_not_met.pdf /data/inbox/"
```

> "Three new requests just arrived in the inbox, the way a fax or portal upload would: a lumbar spine MRI, a knee MRI and a brain MRI. In production they land here on their own."

(Clip: `2 New Requests.mov`)

Step 3: **Cowork runs the queue (Claude app).** Click **Scheduled** > **Prior auth intake** > **Run now**, then **Allow** each tool. Wait about 1.5 minutes; while the indicator flashes grey, it's still running. (Clip: `3 Cowork.mov`)

> "Cowork connects to our app through MCP and calls one tool, run all. It takes in each request, has Claude check it against the policy, and reports what needs people. It has no tool to approve or deny."

While it runs, ask the room: "How many requests sit in your queue right now waiting for someone to open them?"

Step 4: **The new cases in Cowork and the web app (Claude app + `nurse1`).** In Cowork, read the report. (Clip: `4 Cowork.mov`)

> "Three new cases: the knee MRI is missing physical therapy notes, the lumbar MRI is likely approve, the brain MRI is likely deny. No decisions were made. That's for people."

In the web app, refresh the queue and show the 3 new cases with their tiers. Open one: point at the citations marked **✓ found in PDF**, then scroll to the audit log, which starts with **cowork**.

> "Every AI claim cites a page and quote, and code checks each one against the PDF. The audit log shows Cowork brought this case in."

Step 5: **The nurse decides (`nurse1`).** Lumbar MRI: **Approve**, rationale "Meets all criteria", **Submit decision**. Brain MRI: **Pend**, rationale "Needs Medical Director review", **Submit decision**. (Clip: `5 Nurse.mov`)

> "The AI suggested; the nurse decides. A nurse can't deny, and neither can the AI, so this one goes to the medical director."

Step 6: **The doctor denies (`meddir`, private window).** Brain MRI: **Deny**, rationale "Policy criteria not met", **Submit decision**. Scroll to the audit log. (Clip: `6 Dr Deny.mov`)

> "Only the medical director can deny. Every step, by Cowork, the AI, the nurse and the doctor, is on the audit trail."

Step 7: **The leader asks Cowork (Claude app).** Click **+ New** and check that **Prior Auth** is on. Type: "What's our override rate and turnaround time now?" Click **Allow**. (Clip: `7 Cowork.mov`)

> "Now I'm the operations leader. I just ask Cowork, in plain English, from the same live data. Cowork is the operator, not the engine."

Step 8: **The nurse asks AI Assist (`nurse1`).** Open **AI Assist** and ask: "What does the knee MRI policy require for physical therapy before approval?" Point at the source under the answer: policy, page and quote. (Clip: `8 Nurse AI Assist.mov`)

> "The nurse can ask the policy directly. The assistant searches the policy document and answers with the exact page and quote, so she can check it herself. It only reads; it can't decide anything."

**Close the demo:**

> "AI does the reading and the checking. Cowork runs the queue. People keep the decisions. That's how we get to 2.5 days without adding headcount."

**If Cowork fails:** click **Check inbox** in the web app. It runs the same services. Say: "That's the point: Cowork is swappable." Or play the clip for that step.

**Before another run:** in the web app, click the blank space to the right of the **NurseOps Now** title, then **Yes, reset** (about $0.30).

### Slide 9: Every Action, Fully Tracked (2 min)

> "You just saw this live. Every action is logged with who did it and when. Cowork shows up as its own actor, 'cowork', separate from the AI review and from each person.
>
> The log captures the AI's output, the human decision, whether the nurse overrode the AI, the actor and the timestamp. For compliance, you can answer 'who did what, and did the AI influence it' for any case."

### Slide 10: Guardrails Built into the Architecture (2 min)

> "Here's the division of labor in one table. Cowork and Claude read PDFs and scanned faxes, extract procedure and diagnosis codes, and find the exact policy quotes. They do it in seconds, which is the time saving.
>
> Approving is for nurses. Denying is for the medical director only. Cowork has no way to do either."

**Discussion prompt:** "Which of these tasks takes your nurses the most time today?"

### Slide 11: Built for Healthcare Compliance (3 min)

> "Three layers of protection.
>
> **Privacy:** personal details like SSNs, names, birth dates, member IDs and NPIs are removed from logs, chat memory and traces. The case record itself stays complete for staff.
>
> **Security:** logins per role, lockouts after wrong passwords, rate limits, and a guard that blocks prompt injection before the model is even called.
>
> **Clinical accuracy:** code checks every quote Claude gives against the actual PDF text. If a quote doesn't match exactly, the case is forced to 'needs review' for a person. We don't claim the AI never makes mistakes; we make sure a mistake can't slip through unchecked.
>
> We tested it: 44 attacks against the real model, and none got through."

**Be honest if asked:** the AI Assist chat sometimes cites details its tools didn't return (scored 3 out of 5 on one test). It's a known gap.

### Slide 12: Pennies per Run, Hours Saved (2 min)

> "Cost. A Claude review is about 10 cents per new case, and an empty inbox costs nothing. Thirty new requests in a day is about three dollars. Cowork runs on a standard Claude plan, and the hosting costs pennies a day because the server sleeps when idle.
>
> There are hard limits: the app stops AI work at 50 cents per case or 10 dollars per day, and hands the work to people. A runaway automation can't run up a bill."

### Slide 13: A Foundation for Clinical Operations (2 min)

> "Why this design scales. All the rules live in one service layer, and everything else is a thin door into it.
>
> A new policy: upload the PDF and re-index. A new intake channel, like a portal or an EMR feed: one more door into the same services. A new workflow, like appeals or claims auditing: the same MCP pattern, so Cowork can operate it too.
>
> And the storage swaps out for production databases and cloud storage without changing the logic."

**Open the discussion (use the rest of Part 2):** "If you could hand one more workflow to Cowork tomorrow, which would it be?"

---

## Part 3: Close and questions (5 min)

### Slide 14: Common Questions (3 min)

> "A few questions I usually get.
>
> **Can the AI ever deny a case?** No. No tool, screen or service allows it. Only the medical director denies.
>
> **How do we know the citations are accurate?** Code checks every quote against the original PDF. A single mismatch sends the case to manual review.
>
> **What would production take?** HIPAA controls, a signed BAA with the model provider, single sign-on with individual accounts, production database and storage, and a pilot on real cases to measure the turnaround."

**Backup answers:**
- *Why Cowork instead of a scheduler?* "Cowork adds plain-English reports and questions. The trigger is swappable, so a scheduler works too."
- *What if Claude is down?* "The case goes to a person with a warning. Nothing is decided automatically."
- *How would you measure the 40%?* "Turnaround, rework rate, cases reviewed and override rate are already tracked in the app. Measure them in a pilot."

### Slide 15: Open Questions (2 min)

> "I'll leave you with one question: where is the biggest bottleneck in your team's queue today, and if we gave that time back to your nurses, how would it change your clinical outcomes?
>
> The next steps could be a technical deep dive, or a pilot on historical, de-identified cases. Thank you. What questions do you have?"
