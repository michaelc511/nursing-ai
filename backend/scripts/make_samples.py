"""Generate the synthetic prior auth requests (data/samples/) and MRI policies (backend/policies/).

SYNTHETIC — NOT REAL PHI. Names, IDs, NPIs, dates and policy text are invented for the demo.
Run from backend/: python scripts/make_samples.py
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "samples"
POLICIES = ROOT / "backend" / "policies"
W, H = letter
BANNER = "SYNTHETIC — NOT REAL PHI — DEMO ONLY"

SPINE = {"name": "Dr. Maya Thornton, MD", "practice": "Lakeside Spine & Orthopedics",
         "npi": "1999999901", "phone": "(555) 010-2200", "fax": "(555) 010-2201"}
ORTHO = {"name": "Dr. Ben Okafor, MD", "practice": "Riverside Sports Medicine",
         "npi": "1999999902", "phone": "(555) 010-3300", "fax": "(555) 010-3301"}
NEURO = {"name": "Dr. Priya Shah, MD", "practice": "Valley Primary Care",
         "npi": "1999999903", "phone": "(555) 010-4400", "fax": "(555) 010-4401"}


def header(c: canvas.Canvas, page: int, total: int, title: str, top: str, banner: str = BANNER) -> float:
    c.setFont("Courier", 8)
    c.drawString(0.5 * inch, H - 0.4 * inch, f"{top}   PAGE {page}/{total}")
    c.setFillGray(0.35)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, H - 0.6 * inch, banner)
    c.drawCentredString(W / 2, 0.4 * inch, banner)
    c.setFillGray(0)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, H - 1.0 * inch, title)
    c.line(0.75 * inch, H - 1.08 * inch, W - 0.75 * inch, H - 1.08 * inch)
    return H - 1.4 * inch


def lines(c: canvas.Canvas, y: float, rows: list[str], size: int = 10) -> float:
    c.setFont("Helvetica", size)
    for row in rows:
        if row.startswith("## "):
            y -= 4
            c.setFont("Helvetica-Bold", size + 1)
            c.drawString(0.75 * inch, y, row[3:])
            c.setFont("Helvetica", size)
        else:
            c.drawString(0.75 * inch, y, row)
        y -= size + 5
    return y


def build(path: Path, pages: list[tuple[str, list[str]]], top: str, banner: str = BANNER) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle(f"{path.name} ({banner})")
    for i, (title, rows) in enumerate(pages, 1):
        y = header(c, i, len(pages), title, top, banner)
        lines(c, y, rows)
        c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------- requests (forms)

def request_form(patient: dict, prov: dict, service: str, cpt: str, dx: str, icd: str, reason: str) -> list[str]:
    return [
        "## Section 1: Member",
        f"Member name: {patient['name']}        DOB: {patient['dob']}",
        f"Member ID: {patient['member_id']}        Plan: Regional Health Plan (PPO)",
        "## Section 2: Requesting provider",
        f"Provider: {prov['name']}        NPI: {prov['npi']}",
        f"Practice: {prov['practice']}",
        f"Phone: {prov['phone']}        Fax: {prov['fax']}",
        "## Section 3: Service requested",
        f"Service: {service}",
        f"CPT: {cpt}        Units: 1        Setting: Outpatient imaging center",
        f"Diagnosis: {dx}        ICD-10: {icd}",
        "Urgency: Standard",
        "## Section 4: Clinical reason",
        *reason.split("\n"),
        "",
        f"Provider signature: /s/ {prov['name']}        Date: {patient['request_date']}",
    ]


def request(filename: str, prov: dict, pages, folder: Path = OUT) -> Path:
    return build(folder / filename, pages, f"FROM: {prov['fax']}  TO: Health Plan UM Fax (555) 010-9000")


def case_a() -> Path:
    p = {"name": "Jordan Rivers", "dob": "03/14/1979", "member_id": "RHP-100245", "request_date": "10/28/2026"}
    return request("72148_a_complete.pdf", SPINE, [
        ("Prior Authorization Request — Outpatient Imaging", request_form(
            p, SPINE, "MRI lumbar spine without contrast", "72148", "Lumbar radiculopathy", "M54.16",
            "Low back pain radiating to left leg for 10 weeks. Failed 8 weeks of physical therapy\n"
            "and NSAIDs. Positive straight-leg raise on the left. See attached notes.")),
        ("Clinical Note — Office Visit 10/27/2026", [
            "Patient: Jordan Rivers    DOB 03/14/1979",
            "## History",
            "47-year-old with low back pain since mid-August 2026, radiating down the left leg",
            "to the foot with numbness in the L5 distribution. Pain 7/10.",
            "Completed 8 weeks of physical therapy (2x/week) and naproxen 500 mg BID for 6 weeks.",
            "No improvement in radicular symptoms.",
            "## Red flags",
            "No bowel/bladder changes, no fever, no weight loss, no history of cancer or trauma.",
            "## Exam",
            "Positive straight-leg raise left at 40 degrees. Decreased sensation dorsum left foot.",
            "Strength 5/5 except left EHL 4/5. Reflexes symmetric.",
            "## Assessment / Plan",
            "Persistent L5 radiculopathy after 8 weeks of conservative therapy.",
            "Request MRI lumbar spine without contrast to evaluate for disc herniation and",
            "guide possible epidural steroid injection.",
        ]),
        ("Physical Therapy Discharge Summary", [
            "Patient: Jordan Rivers    Therapist: Chris Ng, PT    Clinic: MoveWell PT",
            "Dates of care: 08/29/2026 – 10/24/2026 (8 weeks, 16 visits)",
            "## Treatment",
            "Core stabilization, McKenzie extension protocol, nerve glides, home exercise program.",
            "## Outcome",
            "Back pain improved slightly (8/10 to 7/10). Radicular leg symptoms unchanged.",
            "Oswestry Disability Index 46% at start, 42% at discharge.",
            "## Recommendation",
            "Plateaued with conservative care. Refer back to physician for imaging.",
        ]),
    ])


def case_b() -> Path:
    p = {"name": "Casey Morgan", "dob": "07/02/1985", "member_id": "RHP-100377", "request_date": "10/29/2026"}
    return request("73721_b_missing_pt.pdf", ORTHO, [
        ("Prior Authorization Request — Outpatient Imaging", request_form(
            p, ORTHO, "MRI knee (right) without contrast", "73721", "Pain in right knee, suspected meniscus tear", "M25.561",
            "Right knee pain with catching and swelling for 9 weeks after a twisting injury playing\n"
            "soccer. Patient reports completing physical therapy. PT records to follow.")),
        ("Clinical Note — Office Visit 10/28/2026", [
            "Patient: Casey Morgan    DOB 07/02/1985",
            "## History",
            "41-year-old with right knee pain for about 9 weeks after a twisting injury.",
            "Reports catching and intermittent swelling. States they attended physical therapy",
            "'for several weeks' at an outside clinic. Taking ibuprofen 600 mg as needed.",
            "## Imaging",
            "Right knee X-ray 09/05/2026: no fracture, joint spaces preserved.",
            "## Exam",
            "Medial joint line tenderness. McMurray test positive medially. Mild effusion.",
            "Ligaments stable (Lachman and drawer negative).",
            "## Assessment / Plan",
            "Suspected medial meniscus tear, right knee. Request MRI knee without contrast.",
            "PT records requested from outside clinic; not yet received.",
        ]),
    ])


def case_b_followup() -> Path:
    """Case B's missing PT notes, uploaded later with "Add documents" (not loaded by reset-demo)."""
    return request("73721_b_followup_pt_notes.pdf", ORTHO, [
        ("Physical Therapy Progress Summary", [
            "Patient: Casey Morgan    DOB 07/02/1985    Therapist: Lee Ortiz, PT    Clinic: CoreMotion PT",
            "Dates of care: 09/08/2026 – 10/20/2026 (6 weeks, 12 visits)",
            "## Treatment",
            "Quadriceps and hip strengthening, range of motion, balance work, home exercises.",
            "## Outcome",
            "Strength improved. Catching and locking with pivoting unchanged; swelling after activity.",
            "McMurray remains positive medially.",
            "## Recommendation",
            "Mechanical symptoms persist after 6 weeks of conservative care. Recommend imaging.",
        ]),
    ], folder=OUT / "followup")


def case_c() -> Path:
    p = {"name": "Taylor Brooks", "dob": "11/19/1990", "member_id": "RHP-100512", "request_date": "10/30/2026"}
    return request("70551_c_not_met.pdf", NEURO, [
        ("Prior Authorization Request — Outpatient Imaging", request_form(
            p, NEURO, "MRI brain without contrast", "70551", "Tension-type headache", "G44.209",
            "Recurring headaches for 6 months, worse with work stress. Patient requests an MRI\n"
            "for reassurance.")),
        ("Clinical Note — Office Visit 10/29/2026", [
            "Patient: Taylor Brooks    DOB 11/19/1990",
            "## History",
            "35-year-old with band-like headaches 2–3 times a week for 6 months, worse with stress",
            "and long screen time. Relieved by ibuprofen. No change in pattern.",
            "## Red flags",
            "No sudden 'worst headache', no new neurological symptoms, no seizures, no fever,",
            "no cancer history, no head trauma. Not pregnant. Age under 50.",
            "## Exam",
            "Neurological exam normal, including fundi, cranial nerves, strength and gait.",
            "Mild tenderness of neck and shoulder muscles.",
            "## Assessment / Plan",
            "Chronic tension-type headache. Patient anxious and requests MRI.",
            "Discussed headache diary, sleep, posture and a trial of preventive therapy.",
        ]),
    ])


MANIFEST = {
    "_note": "Per sample: intake channel (README: fax, PDF, portal, provider upload). Synthetic demo data. "
             "The diagnosis now comes from the AI review (AI MK).",
    "72148_a_complete.pdf": {"channel": "fax"},
    "73721_b_missing_pt.pdf": {"channel": "portal"},
    "70551_c_not_met.pdf": {"channel": "upload"},
}

# ---------------------------------------------------------------- policies

POLICY_BANNER = "SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY"
REGISTRY = [
    {"cpt": "72148", "title": "MRI lumbar spine", "number": "RHP-IMG-014", "version": "3.3", "effective": "2026-12-01",
     "file": "72148.pdf", "codes": "72148 (without contrast)"},
    {"cpt": "73721", "title": "MRI knee", "number": "RHP-IMG-022", "version": "2.2", "effective": "2026-12-01",
     "file": "73721.pdf", "codes": "73721 (lower extremity joint, without contrast)"},
    {"cpt": "70551", "title": "MRI brain", "number": "RHP-IMG-005", "version": "4.1", "effective": "2026-12-01",
     "file": "70551.pdf", "codes": "70551 (without contrast)"},
]

POLICY_TEXT = {
    "72148": [
        ("Coverage criteria", [
            "## 1. Purpose",
            "Defines when outpatient MRI of the lumbar spine is medically necessary for members.",
            "## 2. Covered when ONE of the following is documented",
            "A. Low back pain or radicular symptoms lasting 6 weeks or more AND failure of",
            "   at least 6 weeks of conservative therapy (physical therapy, and/or NSAIDs or other",
            "   medication), with documentation of the dates and response.",
            "B. A red flag is present (conservative therapy not required):",
            "   - suspected cauda equina syndrome (saddle numbness, new bowel or bladder change)",
            "   - history of cancer, or unexplained weight loss",
            "   - suspected infection (fever, IV drug use, immunosuppression)",
            "   - suspected fracture (significant trauma, osteoporosis, long-term steroid use)",
            "   - progressive or severe neurological deficit",
            "C. Planning for surgery or an epidural steroid injection after failed conservative care.",
        ]),
        ("Documentation and exclusions", [
            "## 3. Required documentation",
            "- Clinical note with history, duration of symptoms and neurological exam",
            "- Records of conservative therapy (PT notes or medication history with dates)",
            "- Any red flag findings",
            "## 4. Not medically necessary",
            "- Acute low back pain under 6 weeks without red flags",
            "- Imaging requested for reassurance only",
            "## 5. Review",
            "A nurse reviewer applies these criteria. Requests that do not meet them are referred to",
            "a medical director. Only a medical director may issue an adverse determination.",
        ]),
    ],
    "73721": [
        ("Coverage criteria", [
            "## 1. Purpose",
            "Defines when outpatient MRI of the knee is medically necessary for members.",
            "## 2. Covered when ONE of the following is documented",
            "A. Suspected meniscus or ligament tear with mechanical symptoms (locking, catching,",
            "   giving way) or a positive exam test (McMurray, Lachman, drawer), AND a knee X-ray,",
            "   AND failure of at least 4–6 weeks of conservative care (PT, activity change, NSAIDs).",
            "B. Acute injury with inability to bear weight or a locked knee (conservative care not",
            "   required); X-ray first to rule out fracture.",
            "C. Suspected infection, tumor or osteonecrosis.",
            "D. Planning for knee surgery.",
        ]),
        ("Documentation and exclusions", [
            "## 3. Required documentation",
            "- Clinical note with mechanism of injury, symptoms and exam findings",
            "- Knee X-ray report",
            "- Records of conservative care (PT notes with dates and response)",
            "## 4. Not medically necessary",
            "- Knee pain without mechanical symptoms or exam findings, before conservative care",
            "- Osteoarthritis already shown on X-ray, unless surgery is being planned",
            "## 5. Review",
            "A nurse reviewer applies these criteria. Requests that do not meet them are referred to",
            "a medical director. Only a medical director may issue an adverse determination.",
        ]),
    ],
    "70551": [
        ("Coverage criteria", [
            "## 1. Purpose",
            "Defines when outpatient MRI of the brain is medically necessary for members.",
            "## 2. Covered for headache when ONE red flag is documented",
            "- Sudden severe ('worst ever') headache, or a new headache after age 50",
            "- New neurological deficit, papilledema, confusion or seizure",
            "- Headache with fever and neck stiffness, cancer history or immunosuppression",
            "- Clear change in a long-standing headache pattern",
            "- Headache triggered by exertion, cough or position",
            "## 3. Also covered",
            "Known or suspected tumor, stroke, multiple sclerosis, or seizure disorder work-up.",
        ]),
        ("Documentation and exclusions", [
            "## 4. Required documentation",
            "- Clinical note with headache history, pattern and full neurological exam",
            "- Which red flag (if any) is present",
            "## 5. Not medically necessary",
            "- Tension-type or migraine headache with a normal neurological exam and no red flags",
            "- Imaging requested for reassurance only",
            "## 6. Review",
            "A nurse reviewer applies these criteria. Requests that do not meet them are referred to",
            "a medical director. Only a medical director may issue an adverse determination.",
        ]),
    ],
}


# Pages 3-5 (added in v3.3 / v2.2 / v4.1): realistic length, with wording that overlaps the
# coverage criteria on pages 1-2 on purpose, so retrieval has to tell close sections apart.
# Pages 1-2 stay unchanged so existing labels (§2.A ...), pages and mock reviews still hold.

def admin(start: int, urgent_example: str, coding: list[str], history: list[str]) -> list[str]:
    s = start
    return [
        f"## {s}. Expedited review",
        "A request is reviewed within 72 hours when the provider states that waiting could",
        "seriously harm the member's life, health or ability to regain function, for example",
        f"{urgent_example}.",
        f"## {s + 1}. Standard review timelines",
        "A decision is made within 7 calendar days of a complete request. Missing documents",
        "pause the clock; the provider is asked for them within 1 business day.",
        f"## {s + 2}. Peer-to-peer and appeals",
        "The ordering provider may ask for a peer-to-peer discussion with the medical director",
        "within 14 days of an adverse determination. A written appeal may be filed within",
        "180 days and is decided by a reviewer who was not part of the first decision.",
        f"## {s + 3}. Site of service",
        "Outpatient MRI should be done at a freestanding imaging center when one is available",
        "within 30 miles. Hospital outpatient imaging is covered when no such center is nearby.",
        f"## {s + 4}. Coding notes",
        *coding,
        f"## {s + 5}. Policy history",
        *history,
    ]


EXTRA_TEXT = {
    "72148": [
        ("Definitions and repeat imaging", [
            "## 6. Definitions",
            "A. Conservative therapy: a supervised program of physical therapy or a home exercise",
            "   plan directed by a clinician, and/or NSAIDs, muscle relaxants or other medication,",
            "   lasting at least 6 weeks, with the dates and the member's response documented.",
            "B. Red flag: a finding that suggests a serious cause of back pain, such as cauda equina",
            "   syndrome, cancer, infection, fracture or a progressive neurological deficit.",
            "C. Radicular symptoms: pain, numbness or tingling that follows a nerve root pattern",
            "   into the buttock or leg, with or without weakness.",
            "D. Neurological deficit: objective weakness, reflex loss or sensory loss on exam that",
            "   matches a nerve root level.",
            "## 7. Repeat lumbar MRI",
            "A. Covered when new or clearly worse symptoms appear after a prior lumbar MRI, or a",
            "   new red flag is documented.",
            "B. Covered to follow a known tumor, infection or fracture when the result will change",
            "   treatment.",
            "C. Not covered within 12 months of a prior lumbar MRI when symptoms are unchanged.",
            "## 8. Post-operative imaging",
            "A. Covered within 6 weeks of lumbar surgery for suspected infection, hematoma or a",
            "   new neurological deficit.",
            "B. Covered more than 6 weeks after surgery for recurrent radicular symptoms that have",
            "   not improved with at least 6 weeks of conservative therapy.",
        ]),
        ("Prior imaging, contrast and special populations", [
            "## 9. Prior imaging",
            "- Plain X-rays are not required before MRI for radicular symptoms.",
            "- X-rays are required first after significant trauma, or in members over 70 or with",
            "  osteoporosis, to look for a fracture.",
            "- A CT myelogram may be used instead of MRI when MRI cannot be done safely.",
            "## 10. Contrast",
            "MRI with contrast (72149) or with and without contrast (72158) is reviewed under a",
            "separate policy. Contrast is usually only needed after prior surgery, or for",
            "suspected infection or tumor.",
            "## 11. Special populations",
            "A. Members under 18: covered for back pain lasting 4 weeks or more, night pain, or",
            "   any red flag. Conservative therapy is not required for night pain.",
            "B. Pregnancy: MRI without contrast may be done in any trimester when the result will",
            "   change care. Gadolinium contrast should be avoided.",
            "C. Implanted devices: a pacemaker, neurostimulator or metal implant must be checked",
            "   as MRI-conditional before the scan is scheduled.",
            "## 12. Sedation and open MRI",
            "Sedation or anesthesia is covered when the member cannot stay still because of",
            "claustrophobia, pain or a developmental condition, and this is documented. An open",
            "MRI may be used for members who cannot fit in a standard scanner.",
        ]),
        ("Review process and administration", admin(
            13, "suspected cauda equina syndrome",
            ["Only one lumbar MRI is approved per request. Thoracic (72146) and cervical (72141)",
             "spine MRI need their own requests under their own policies."],
            ["Version 3.3 (2026-12-01): added definitions, repeat and post-operative imaging,",
             "special populations and review timelines. Version 3.2 (2026-07-01): red flag list",
             "updated."])),
    ],
    "73721": [
        ("Definitions and repeat imaging", [
            "## 6. Definitions",
            "A. Conservative care: physical therapy or a supervised home exercise plan, activity",
            "   change, bracing and/or NSAIDs for at least 4 to 6 weeks, with dates and response.",
            "B. Mechanical symptoms: locking, catching or the knee giving way during normal",
            "   activity.",
            "C. Positive exam test: a McMurray, Lachman, anterior or posterior drawer, or pivot",
            "   shift test recorded as positive by the examining clinician.",
            "D. Unable to bear weight: the member cannot take four steps, both right after the",
            "   injury and at the visit.",
            "## 7. Repeat knee MRI",
            "A. Covered when a new injury or clearly new mechanical symptoms appear after a prior",
            "   knee MRI.",
            "B. Not covered within 12 months of a prior MRI of the same knee when symptoms are",
            "   unchanged.",
            "## 8. Post-operative imaging",
            "A. Covered after meniscus repair or ligament reconstruction for a suspected re-tear,",
            "   with new mechanical symptoms and a positive exam test.",
            "B. Covered at any time for suspected infection after knee surgery.",
            "C. Routine imaging after surgery to check healing is not covered.",
        ]),
        ("Prior imaging, contrast and special populations", [
            "## 9. Prior imaging",
            "- A weight-bearing knee X-ray from the last 6 months is required before MRI.",
            "- After an acute injury, X-ray comes first to rule out a fracture (Ottawa knee rules).",
            "- X-ray is not needed first for a suspected infection or tumor in a child.",
            "## 10. Contrast",
            "MR arthrography (joint contrast) and MRI with IV contrast are reviewed under a",
            "separate policy. Contrast is mainly used after prior meniscus surgery.",
            "## 11. Special populations",
            "A. Members under 18: covered for suspected osteochondritis dissecans, a locked knee",
            "   or a suspected tumor. Growth plate injuries need an X-ray first.",
            "B. Athletes: return-to-play timing alone does not make a knee MRI medically",
            "   necessary.",
            "C. Implanted devices: knee replacement hardware limits MRI; CT is usually preferred.",
            "## 12. Osteoarthritis",
            "MRI is not medically necessary to diagnose or stage osteoarthritis; X-ray is the test",
            "of choice. MRI may be covered when surgery other than joint replacement is planned.",
        ]),
        ("Review process and administration", admin(
            13, "a locked knee that cannot be straightened",
            ["One knee per request; MRI of both knees needs two requests. Ankle and hip MRI",
             "under the same CPT code are reviewed under the joint imaging policy."],
            ["Version 2.2 (2026-12-01): added definitions, repeat and post-operative imaging,",
             "special populations and review timelines. Version 2.1 (2026-04-01): conservative",
             "care set at 4 to 6 weeks."])),
    ],
    "70551": [
        ("Definitions and repeat imaging", [
            "## 7. Definitions",
            "A. Red flag: a headache feature that suggests a serious cause, such as bleeding,",
            "   tumor, infection or raised pressure inside the skull.",
            "B. New headache after age 50: a type of headache the member has never had before,",
            "   starting at age 50 or older.",
            "C. Change in pattern: a clear change in how often, how severe or what kind of",
            "   headache a member with a long history of headaches has.",
            "D. Normal neurological exam: no weakness, numbness, vision change, papilledema, gait",
            "   problem or change in mental status on a documented exam.",
            "## 8. Repeat brain MRI",
            "A. Covered to follow a known tumor, multiple sclerosis or other disease when the",
            "   result will change treatment.",
            "B. Covered for new or worse neurological symptoms after a prior brain MRI.",
            "C. Not covered within 12 months of a prior brain MRI for the same stable headache.",
            "## 9. Migraine and tension-type headache",
            "Imaging is not medically necessary for a typical migraine or tension-type headache",
            "with a normal neurological exam, even when the headache is frequent or severe,",
            "unless a red flag listed in section 2 is present.",
        ]),
        ("Prior imaging, contrast and special populations", [
            "## 10. Prior imaging",
            "- CT of the head, not MRI, is preferred first for a sudden severe headache or head",
            "  trauma in the first 24 hours, to look for bleeding.",
            "- MRI may follow a normal CT when symptoms continue or a red flag remains.",
            "## 11. Contrast",
            "MRI with contrast (70552) or with and without contrast (70553) is reviewed under a",
            "separate policy. It is usually needed for tumor, infection or multiple sclerosis.",
            "## 12. Special populations",
            "A. Members under 18: covered for headache that wakes the child from sleep, morning",
            "   vomiting, a change in behavior or school performance, or an abnormal exam.",
            "B. Pregnancy: MRI without contrast may be done when a red flag is present.",
            "   Gadolinium contrast should be avoided.",
            "C. Implanted devices: a pacemaker, cochlear implant or aneurysm clip must be checked",
            "   as MRI-conditional before the scan is scheduled.",
            "## 13. Sedation",
            "Sedation is covered when the member cannot stay still because of age,",
            "claustrophobia or a developmental condition, and this is documented.",
        ]),
        ("Review process and administration", admin(
            14, "a new seizure or a sudden severe headache with a normal CT",
            ["Only one brain MRI is approved per request. MRI of the orbits, face or neck and MR",
             "angiography need their own requests under their own policies."],
            ["Version 4.1 (2026-12-01): added definitions, repeat imaging, migraine guidance,",
             "special populations and review timelines. Version 4.0 (2026-01-01): new headache",
             "after age 50 added as a red flag."])),
    ],
}


def policy(entry: dict) -> Path:
    head = [
        f"Policy number: {entry['number']}        Version: {entry['version']}",
        f"Effective date: {entry['effective']}        Applies to: Regional Health Plan (all lines)",
        f"CPT codes: {entry['codes']}",
        "",
    ]
    pages = [(f"Medical Policy: {entry['title']} — {title}", (head if i == 0 else []) + rows)
             for i, (title, rows) in enumerate(POLICY_TEXT[entry["cpt"]] + EXTRA_TEXT[entry["cpt"]])]
    return build(POLICIES / entry["file"], pages, "REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT", POLICY_BANNER)


def write_policies() -> None:
    for entry in REGISTRY:
        print(f"wrote {policy(entry).relative_to(ROOT)}")
    (POLICIES / "index.json").write_text(json.dumps(REGISTRY, indent=2) + "\n")
    print("wrote backend/policies/index.json")


if __name__ == "__main__":
    import sys
    if "--policies-only" in sys.argv:      # regenerate policies without touching the sample requests
        write_policies()
        sys.exit(0)
    for old in ("72148_b_missing_pt.pdf", "72148_c_not_met.pdf", "followup/72148_b_followup_pt_notes.pdf"):
        (OUT / old).unlink(missing_ok=True)
    for f in (case_a, case_b, case_c, case_b_followup):
        print(f"wrote {f().relative_to(ROOT)}")
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print("wrote data/samples/manifest.json")
    write_policies()
