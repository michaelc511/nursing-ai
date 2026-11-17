# Script: NurseOps_Now_AI_Prior_Authorization.pdf

Speaker script for the 15-slide NotebookLM deck (navy and gold design, starts "NurseOps Now: AI for faster prior authorization, Run by Claude Cowork"). 45 minutes, focus on Claude Cowork.

Facts come from `docs/demo/2-talk-notes.md`, `docs/demo/1-short_script.md` and `docs/demo/4-demo-script.md`. The timing split below is Claude's suggestion, built around your 10-minute intro and 30-minute discussion.

| Part | Slides | Time |
| --- | --- | --- |
| 1. Intro | 1–5 | 10 min |
| 2. Claude Cowork: live demo and discussion | 6–13 (live demo after slide 8) | 30 min |
| 3. Close and questions | 14–15 | 5 min |

**Fix on the slides, or correct them out loud** (the deck says something the docs don't support):
- Slide 6 has a garbled label ("Headlı 1"), and it says Cowork runs "every 15 minutes". Today you run the task on demand or daily; every 15 minutes is the production plan.
- Slide 10 shows a made-up person, "Nurse Sarah Jenkins". Your real log shows `nurse1`. Say "a nurse".
- Slide 12 says "no patient data leaves the secure server" and "entirely preventing hallucinations". OCR runs locally, but the request PDF **is** sent to Claude through the API, which is covered by a BAA in production. Quote checks force a human review on any mismatch; they don't make the AI perfect.
- Slide 13 says "Infinite Scale" and "40% Faster". 40% is a **goal**, not measured yet, and "infinite" is too strong. Say "easy to extend".

---

## Part 1: Intro (10 min)

### Slide 1: NurseOps Now (1 min)

**Before you start:** the live app is awake, you're logged in as `nurse1`, `meddir` is open in a private window, and the Prior Auth connector is on in Cowork.

> "Good morning. I'm Mike Chang. Today I'll show you NurseOps Now, an AI prototype that helps nurses get prior authorizations done faster. It's live, it runs on Claude, and it's operated by Claude Cowork. Everything you'll see uses synthetic data, so there are no real patients.
>
> About 10 minutes on the problem and the idea, then most of our time on Cowork, with a live demo and discussion, and a few minutes for questions at the end."

### Slide 2: The waiting game (2 min)

> "A regional health plan gets about 15,000 prior authorization requests a month by fax, PDF, portal and upload. Nurses read every one by hand, often 10 pages or more.
>
> Two numbers tell the story. 4.2 days: the average wait for a decision. 22%: the share of requests that need rework because something is missing.
>
> So patients wait for care, nurses do paperwork instead of clinical work, and providers call to ask where their request is."

### Slide 3: A tireless assistant for your clinical team (2 min)

> "NurseOps Now is an assistant for the clinical team. It does three things.
>
> It reads every request the moment it arrives. It prepares the case against the plan's policy rules, with citations. And it hands the case to a nurse, because the nurse makes the final call.
>
> The goal is 40% faster, from 4.2 days to about 2.5, with no added headcount. That's a goal; a pilot on real work would measure it."

### Slide 4: Where AI moves the needle (3 min)

> "Three opportunities.
>
> **Catch missing paperwork immediately.** Claude reads the request, pulls out the patient, the procedure and the diagnosis, and flags what's missing, like physical therapy notes. It drafts the request to the provider. Rework starts on day one instead of day four.
>
> **A study buddy for the nurse.** Claude compares the request to the policy and shows exactly where each rule is met, with the page and the quote. It suggests a tier: likely approve, needs review, or likely deny. The nurse decides.
>
> **Keep queues visible.** Anyone can ask 'Where is this request?' or 'What's stuck?' and get an answer from live data. Fewer status calls."

### Slide 5: The absolute boundary (2 min)

> "This is the one rule. AI reads and cites; nurses decide.
>
> On the left, the AI reads complex documents and suggests a tier, and Cowork keeps the queue moving. It prepares the desk.
>
> On the right, only people make decisions. Nurses approve or pend. Only the medical director can deny.
>
> This is enforced in the service layer, not just on the screen. No tool, screen or automation can get around it.
>
> Now let's look at what keeps the queue moving: Claude Cowork."

---

## Part 2: Claude Cowork, live demo and discussion (30 min)

### Slide 6: The shift supervisor that never sleeps (3 min)

> "Think of Cowork as a shift supervisor for the intake queue. Cowork is Claude in the desktop app, connected to our system.
>
> It runs a scheduled task called 'Prior auth intake'. The task picks up every new request, turns it into a case, has Claude review it, and then reports in plain English exactly what's missing and what needs a human.
>
> For this demo I run it on demand. In production it would run every 15 minutes or when a new request arrives.
>
> The key idea: Cowork is the operator, not the engine. Replace it with a plain scheduler and nothing else changes. Cowork adds the report and lets leaders ask questions."

### Slide 7: A secure, fixed toolset (3 min)

> "Cowork connects through a secure connector called 'Prior Auth'. Under the hood it's MCP, the Model Context Protocol, an open standard for giving AI a set of tools. The connection is protected by a token.
>
> Cowork gets exactly 7 tools, all about running the queue: take in requests, review a case, look up cases, find stuck ones, and get metrics.
>
> There's no tool to approve, pend or deny. And MCP calls the same service layer as the web app, so every rule and every log applies to Cowork too. It can't work outside that space."

### Slide 8: How requests flow through Cowork (2 min)

> "Here's the flow you'll see live. One: faxes and uploads arrive in the queue. Two: each becomes a structured case. Three: Claude checks it against the policy criteria, and code checks Claude's quotes. Four: the prepared case waits for a nurse.
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

While it runs, ask the room: "How long does a new request sit in your queue before someone opens it?"

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

### Slide 9: Eliminating the 3-day delay (2 min)

> "Here's what you just saw, as a timeline. Before: the fax arrives on day one, sits for three days, and on day four a nurse finds the physical therapy notes are missing. The clock restarts.
>
> With NurseOps Now: the fax arrives on day one, Cowork runs, Claude flags the missing notes the same day, and the request to the provider is already drafted. That's aimed straight at the 22% rework, and providers hear about the gap right away instead of days later."

**Discussion prompt:** "What share of your rework is missing documents versus something else?"

### Slide 10: Total transparency (2 min)

> "Every action is recorded. Cowork appears in the log as its own actor, 'cowork': it brought the case in and flagged what was missing. Then a nurse reviewed the citations and pended the case for the medical director.
>
> The log captures the AI's output, the human decision, whether the nurse overrode the AI, who acted and when. Every citation points back to the original PDF. No black boxes."

### Slide 11: AI cannot make the call (2 min)

> "Three locks on decision authority.
>
> **No access:** Cowork has no tool to approve or deny.
>
> **Forced verification:** if a quote from Claude doesn't match the PDF exactly, the system forces a manual review.
>
> **Medical director only:** only the medical director's role can issue a denial."

**Discussion prompt:** "Would your medical directors want the AI's tier shown to them, or hidden until after they decide?"

### Slide 12: Built for healthcare compliance (2 min)

> "**Privacy:** designed for HIPAA. OCR on scanned faxes runs on our own server, and personal details are removed from logs, traces and chat memory. The request itself goes to Claude through the API, which in production is covered by a business associate agreement.
>
> **Guardrails:** rate limits and cost caps stop runaway automation.
>
> **Testing:** an evaluation suite, plus 44 prompt-injection attacks on the real model with none getting through.
>
> **Oversight:** code checks every quote against the source, so a wrong quote can't reach a decision without a person reviewing it."

**Be honest if asked:** the AI Assist chat sometimes cites details its tools didn't return (scored 3 out of 5 on one test). It's a known gap.

### Slide 13: Faster decisions, zero new headcount (2 min)

> "The business case. The goal is 40% faster, from 4.2 days to 2.5. It's a goal, and a pilot would measure it.
>
> The cost is about 10 cents per new case on real Claude, nothing for an empty inbox, and the app stops AI work at 50 cents per case or 10 dollars a day.
>
> It's easy to extend. A new policy is a PDF upload and a re-index. A new intake channel, like a portal or fax line, is one more door into the same services. And the same Cowork pattern can operate new workflows, like appeals or claims auditing."

**Open the discussion (use the rest of Part 2):** "If Cowork could run one more workflow for you tomorrow, which would it be?"

---

## Part 3: Close and questions (5 min)

### Slide 14: Where to focus next (3 min)

> "Three questions for you, to decide where a pilot would help most.
>
> Which prior auth policies cause your clinical team the most friction?
>
> How do you measure provider frustration with wait times today?
>
> And what would it take to test this on your historical, de-identified cases? That's how we'd measure the 40%."

**Backup answers:**
- *Can the AI deny?* "No. No tool, screen or service allows it. Only the medical director."
- *Why Cowork instead of a scheduler?* "Cowork adds plain-English reports and questions. The trigger is swappable."
- *What if Claude is down?* "The case goes to a person with a warning. Nothing is decided automatically."
- *What would production take?* "HIPAA controls, a BAA, single sign-on, production database and storage, and a pilot to measure turnaround."

### Slide 15: Questions? (2 min)

> "Thank you. The app is live, and I'm happy to go back to any part of the demo. What questions do you have?"
