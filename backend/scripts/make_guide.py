"""Generate the Guide Me knowledge base PDF (backend/knowledge/guide_me.pdf).

Source for the Guide Me help today (scripted) and its RAG + LLM later: terms, roles, rules,
statuses, workflows and how Guide Me picks the next step. Keep in step with README "How to use",
frontend/src/guide.ts and backend/app/services/. Run from backend/: python scripts/make_guide.py
"""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

OUT = Path(__file__).resolve().parents[1] / "knowledge" / "guide_me.pdf"
VERSION = "1.0"
TEAL = colors.HexColor("#0b6e8a")
SOFT = colors.HexColor("#f0f7f9")
LINE = colors.HexColor("#dbe4e8")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=TEAL, fontSize=18, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=TEAL, fontSize=13, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.5, leading=13)
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.5, leading=11)
CELLB = ParagraphStyle("CB", parent=CELL, fontName="Helvetica-Bold")
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, textColor=colors.grey)


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [p(f"• {t}") for t in items]


def table(head, rows, widths):
    data = [[p(h, CELLB) for h in head]] + [[p(c, CELL) for c in r] for r in rows]
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT), ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def section(title, *flow):
    return [p(title, H2), *flow, Spacer(1, 4)]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(0.75 * inch, 0.45 * inch,
                      f"NurseOps Now · Guide Me knowledge base v{VERSION} · {date.today():%Y-%m-%d} · synthetic demo content")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


GLOSSARY = [
    ("Prior authorization (PA)", "Approval the health plan requires before certain services (like an MRI) are covered."),
    ("Utilization management (UM)", "The health plan team that reviews PA requests against medical policy."),
    ("Case", "One prior authorization request in NurseOps Now: its documents, status, decisions and audit log."),
    ("Document ID", "Intake reference: CHANNEL-YYYYMMDD-NNNN (channel prefix, date received, case number), e.g. FAX-20261110-0001."),
    ("FAX", "Document ID prefix: the request arrived by fax."),
    ("PRT", "Document ID prefix: the request arrived through the provider portal (the plan's website for providers)."),
    ("UPL", "Document ID prefix: the provider uploaded the request (e.g. PDF upload)."),
    ("DOC", "Document ID prefix used when the channel is unknown."),
    ("Channel", "How a request arrived: Fax, Provider portal or Provider upload."),
    ("Member", "The patient covered by the health plan. Member ID looks like RHP-100245 (synthetic)."),
    ("Provider", "The doctor or practice requesting the service. NPI = their national provider number."),
    ("CPT code", "5-digit procedure code naming the requested service. 72148 = MRI lumbar spine without contrast; "
                 "73721 = MRI knee (lower extremity joint) without contrast; 70551 = MRI brain without contrast."),
    ("ICD-10 code", "Diagnosis code: why the service is requested. e.g. M54.16 lumbar radiculopathy, "
                    "M25.561 right knee pain, G44.209 tension-type headache."),
    ("Medical policy", "The plan's written criteria for a service (number, version, effective date). "
                       "Picked by CPT code: RHP-IMG-014 lumbar, RHP-IMG-022 knee, RHP-IMG-005 brain."),
    ("Medical necessity", "Whether the request meets the policy criteria."),
    ("Conservative therapy", "Non-surgical care tried first, e.g. physical therapy (PT), medication (NSAIDs), activity change."),
    ("Red flag", "A warning sign that allows imaging without conservative therapy first (e.g. cancer history, infection, "
                 "fracture, cauda equina, new neurological deficit, sudden worst headache)."),
    ("Rationale", "The short reason a reviewer must write for every decision."),
    ("Adverse determination", "A denial for medical necessity. Only a Medical Director may issue one."),
    ("Peer-to-peer", "A call where the requesting doctor discusses a case with the Medical Director."),
    ("Turnaround", "Time from request received to decision. CMS rule (in effect Jan 1, 2026, for Medicare Advantage, "
                   "Medicaid, CHIP and ACA marketplace plans): 7 calendar days standard, 72 hours expedited."),
    ("Standard / Expedited", "Normal urgency vs urgent requests with the shorter deadline."),
    ("Rework", "A request sent back because information was missing (status Incomplete). Today about 22% of requests."),
    ("Provider request", "Message asking the provider for missing documents, sent when a case becomes Incomplete."),
    ("AI tier", "Claude's suggestion after review: likely approve, needs review or likely deny. A suggestion only."),
    ("Override", "Flag set when the human decision disagrees with the AI tier (e.g. Approved when AI said likely deny)."),
    ("Audit log", "Record of every action: who, what, when (status changes, decisions, downloads, sync)."),
    ("UM platform", "The plan's system of record; decisions are pushed there (mocked in the demo)."),
    ("Synced", "Decision sent to the UM platform and the provider notified."),
    ("Stuck case", "A case waiting in the same open status for more than 2 days."),
    ("Simulated AI check", "Demo-only buttons (Check passed / Missing info) that stand in for Claude's review until it is connected."),
    ("PHI", "Protected health information. The demo uses synthetic data only."),
]

ROLES = [
    ("Intake Coordinator", "intake1", "Riley Chen",
     "Brings in new requests (Check inbox), runs the check on Received cases, adds documents to Incomplete cases. Cannot decide."),
    ("Nurse", "nurse1, nurse2", "Nora Diaz, RN; Sam Patel, RN",
     "Reviews Ready cases against the policy. Can Approve or Pend. Cannot Deny: pends for the Medical Director instead."),
    ("Medical Director", "meddir", "Dr. Alex Kim, MD",
     "Decides Pended cases and is the only role that can Deny. Can also decide any Ready case. Does peer-to-peer calls."),
    ("System", "(automatic)", "",
     "Sends decisions to the UM platform, notifies the provider, marks cases Synced, writes the audit log."),
    ("AI (Claude, from Phase 3)", "(automatic)", "",
     "Reads the request, checks completeness, compares to the policy with page + quote citations, suggests a tier. Never decides."),
]

PERMS = [
    ("View queue, cases, PDFs, audit log, metrics", "yes", "yes", "yes"),
    ("View / download medical policies", "yes", "yes", "yes"),
    ("Download a request PDF (logged in audit log)", "yes", "yes", "yes"),
    ("Check inbox / add documents", "yes", "yes", "yes"),
    ("Approve or Pend", "no", "yes", "yes"),
    ("Deny", "no", "no", "yes"),
]

STATUSES = [
    ("Received", "New request stored; waiting for the check.", "Incomplete, Ready for review"),
    ("Incomplete", "Something is missing; provider asked for it.", "Received (when documents arrive)"),
    ("Ready for review", "Complete; waiting for a human decision.", "Approved, Pended, Denied (human only)"),
    ("Pended", "On hold, usually for the Medical Director.", "Ready for review (review resumes)"),
    ("Approved", "Human approved it.", "Synced"),
    ("Denied", "Medical Director denied it.", "Synced"),
    ("Synced", "Sent to UM platform; provider notified. Final.", "(none)"),
]

RULES = [
    "AI never decides. Only a Nurse or Medical Director sets Approved or Pended, and only the Medical Director can Deny.",
    "Every decision needs a written rationale.",
    "Statuses follow the order above; anything else is rejected (e.g. a Received or Incomplete case cannot be decided).",
    "Incomplete cases trigger a provider request; new documents send the case back to Received for another check.",
    "Approved and Denied cases are sent to the UM platform and the provider is notified, then become Synced.",
    "Every action is in the audit log, including request PDF downloads.",
    "All PDFs (requests and policies) need a staff login. Never copy member details into email or chat.",
    "Turnaround targets: decide standard requests within 7 calendar days and expedited within 72 hours; flag anything waiting more than 2 days.",
    "Lumbar MRI: 6+ weeks PT or medication first unless a red flag. Knee MRI: mechanical symptoms or positive exam + X-ray + 4–6 weeks "
    "conservative care, unless acute injury. Brain MRI for headache: needs a red flag.",
]

W1 = [
    ("1", "Intake Coordinator · intake1", "Click Check inbox.", "New cases appear as Received."),
    ("2", "Intake Coordinator · intake1", "Open case #1 (lumbar MRI), read it, click Check passed.", "Ready for review."),
    ("3", "Nurse · nurse1", "Sign in, open case #1, compare with the Policy tab, Approve with a reason.", "Approved → Synced; audit shows nurse1."),
    ("4", "Nurse · nurse1", "Open case #3 (brain MRI, no red flags), Pend for the Medical Director.", "Pended."),
    ("5", "Medical Director · meddir", "Sign in, open case #3, Deny with a reason.", "Denied → Synced."),
    ("✗", "Nurse tries to Deny", "Deny is not offered; the server blocks it.", "Blocked (403)."),
]
W2 = [
    ("1", "Intake Coordinator · intake1", "Open case #2 (knee MRI), click Missing info.", "Incomplete; provider request sent; rework rate rises."),
    ("2", "Nurse · nurse1", "Open case #2.", "No decision possible while Incomplete."),
    ("3", "Intake Coordinator · intake1", "Add documents: the PT notes.", "Back to Received; 2 documents."),
    ("4", "Intake Coordinator · intake1", "Click Check passed.", "Ready for review."),
    ("5", "Nurse · nurse2", "Approve with a reason (6 weeks PT, knee still catching).", "Approved → Synced."),
    ("alt", "Nobody", "Provider never responds.", "After 2 days the case shows as stuck."),
]

GUIDE_ORDER = [
    ("1", "No cases yet", "Intake Coordinator", "Click Check inbox."),
    ("2", "Any Received", "Intake Coordinator", "Open the case, read it, click Check passed or Missing info."),
    ("3", "Any Ready for review", "Nurse (Medical Director can too)", "Open it, compare with the policy, Approve or Pend."),
    ("4", "Any Pended", "Medical Director", "Open it, Deny or Approve with a reason."),
    ("5", "Any Incomplete", "Intake Coordinator", "Add the missing documents."),
    ("6", "All Synced", "Everyone", "Look at the results cards. Done."),
]

FAQ = [
    ("Who am I and what do I do?", "Guide Me reads your role from your sign-in and lists your steps (see Roles)."),
    ("Why can't I deny?", "Only the Medical Director can deny (adverse determination). Pend it for MD review."),
    ("Why are there no decision buttons?", "The case isn't Ready for review or Pended, or your role can't decide (Intake Coordinator)."),
    ("What does PRT / UPL / FAX mean?", "How the request arrived: Provider portal, Provider upload, Fax."),
    ("What is 72148?", "CPT code for MRI lumbar spine without contrast."),
    ("Where is the policy?", "On a case: the Policy tab. On the home page: Medical policies, below the queue."),
    ("What is an override?", "The human decision disagreed with the AI tier; it's tracked as a quality metric."),
    ("Is this real patient data?", "No. Everything is synthetic."),
    ("What's the password?", "In demo mode it's filled in for you; just pick a user and sign in."),
]


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="NurseOps Now — Guide Me knowledge base", author="NurseOps Now")
    f = [p("NurseOps Now — Guide Me knowledge base", H1),
         p(f"Version {VERSION} · {date.today():%B %d, %Y} · Source for the Guide Me assistant (scripted today; RAG + LLM later). "
           "Synthetic demo content, not a real health plan document.", SMALL), Spacer(1, 8)]
    f += section("1. About NurseOps Now", *bullets([
        "Helps prior authorization nurses at a regional health plan review MRI requests faster.",
        "The problem: ~15,000 requests a month, 4.2-day average turnaround, 22% need rework for missing information, providers call for status.",
        "The goal: cut turnaround about 40% (to ~2.5 days) with no extra staff, keeping clinical quality and compliance.",
        "How: check completeness at intake and ask the provider right away; Claude prepares a cited summary against the policy; "
        "status is always visible. Humans make every decision.",
    ]))
    f += section("2. Terms you'll see", table(["Term", "Meaning"], GLOSSARY, [1.8, 5.2]))
    f += section("3. Roles and logins", table(["Role", "Login", "Demo person", "What they do"],
                                              ROLES, [1.3, 0.9, 1.3, 3.5]),
                 Spacer(1, 6), table(["Action", "Intake Coordinator", "Nurse", "Medical Director"], PERMS, [3.2, 1.3, 1.0, 1.5]),
                 p("Password: in demo mode the sign-in screen fills it in. It is never written in this guide.", SMALL))
    f += section("4. Case statuses", table(["Status", "Meaning", "Can move to"], STATUSES, [1.3, 3.2, 2.5]))
    f += section("5. Rules", *bullets(RULES))
    f.append(PageBreak())
    f += section("6. Workflows (who does what, in order)",
                 p("<b>W1: Complete request → decision, with escalation to the Medical Director</b>"),
                 table(["Step", "Who", "Does", "Sees"], W1, [0.4, 1.7, 3.0, 1.9]), Spacer(1, 6),
                 p("<b>W2: Incomplete request → provider sends documents → decision</b>"),
                 table(["Step", "Who", "Does", "Sees"], W2, [0.4, 1.7, 3.0, 1.9]))
    f += section("7. How Guide Me picks your next step",
                 p("Guide Me looks at who is signed in and every case's status, finds the first stage below that has work, "
                   "and tells you the next action in plain words. If the stage belongs to another role, it says: "
                   "\"This step is for the &lt;role&gt;. Click Sign out (top right), then sign in as &lt;login&gt;.\" "
                   "It outlines the button to click and updates after every action, even across sign-out and sign-in."),
                 table(["Order", "When", "Who", "Next step"], GUIDE_ORDER, [0.5, 1.5, 1.8, 3.2]))
    f += section("8. Demo cases", table(["Case", "Request", "Channel", "What should happen"], [
        ("#1", "MRI lumbar spine (72148) · lumbar radiculopathy, 8 weeks PT done", "Fax (FAX)", "Check passed → Nurse approves."),
        ("#2", "MRI knee (73721) · suspected meniscus tear, PT notes missing", "Provider portal (PRT)",
         "Missing info → PT notes added → Nurse approves."),
        ("#3", "MRI brain (70551) · tension headache, no red flags", "Provider upload (UPL)",
         "Check passed → Nurse pends → Medical Director denies."),
    ], [0.5, 3.2, 1.4, 1.9]))
    f += section("9. Screens", *bullets([
        "<b>Sign in:</b> pick a user; Guide Me and Dark mode at the top.",
        "<b>Home:</b> results cards (turnaround, rework, cases reviewed, override rate), intro, Unit board, case queue "
        "(sortable: #, Document ID, Channel, Description, Status, AI tier, Received), Medical policies row below.",
        "<b>Case:</b> request and Policy tabs with Download, Simulated AI check (demo), AI review, decision form, audit log.",
        "<b>Help:</b> the ? button (About, this screen, workflow) and Guide Me chat (bottom left). The AI assistant will sit on the right later.",
    ]))
    f += [KeepTogether(section("10. Common questions", table(["Question", "Answer"], FAQ, [2.3, 4.7])))]
    doc.build(f, onFirstPage=footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    print(f"wrote {build().relative_to(OUT.parents[2])}")
