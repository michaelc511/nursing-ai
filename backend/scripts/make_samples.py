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
    "_note": "Per sample: intake channel (README: fax, PDF, portal, provider upload) and the diagnosis on its "
             "request form. Synthetic demo data; from Phase 3 Claude reads these from the document.",
    "72148_a_complete.pdf": {"channel": "fax", "diagnosis": "Lumbar radiculopathy, left leg (M54.16)"},
    "73721_b_missing_pt.pdf": {"channel": "portal", "diagnosis": "Right knee pain, suspected meniscus tear (M25.561)"},
    "70551_c_not_met.pdf": {"channel": "upload", "diagnosis": "Tension-type headache (G44.209)"},
}

# ---------------------------------------------------------------- policies

POLICY_BANNER = "SYNTHETIC DEMO POLICY — NOT A REAL HEALTH PLAN POLICY"
REGISTRY = [
    {"cpt": "72148", "title": "MRI lumbar spine", "number": "RHP-IMG-014", "version": "3.2", "effective": "2026-07-01",
     "file": "72148.pdf", "codes": "72148 (without contrast)"},
    {"cpt": "73721", "title": "MRI knee", "number": "RHP-IMG-022", "version": "2.1", "effective": "2026-04-01",
     "file": "73721.pdf", "codes": "73721 (lower extremity joint, without contrast)"},
    {"cpt": "70551", "title": "MRI brain", "number": "RHP-IMG-005", "version": "4.0", "effective": "2026-01-01",
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


def policy(entry: dict) -> Path:
    head = [
        f"Policy number: {entry['number']}        Version: {entry['version']}",
        f"Effective date: {entry['effective']}        Applies to: Regional Health Plan (all lines)",
        f"CPT codes: {entry['codes']}",
        "",
    ]
    pages = [(f"Medical Policy: {entry['title']} — {title}", (head if i == 0 else []) + rows)
             for i, (title, rows) in enumerate(POLICY_TEXT[entry["cpt"]])]
    return build(POLICIES / entry["file"], pages, "REGIONAL HEALTH PLAN — UTILIZATION MANAGEMENT", POLICY_BANNER)


if __name__ == "__main__":
    for old in ("72148_b_missing_pt.pdf", "72148_c_not_met.pdf", "followup/72148_b_followup_pt_notes.pdf"):
        (OUT / old).unlink(missing_ok=True)
    for f in (case_a, case_b, case_c, case_b_followup):
        print(f"wrote {f().relative_to(ROOT)}")
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print("wrote data/samples/manifest.json")
    for entry in REGISTRY:
        print(f"wrote {policy(entry).relative_to(ROOT)}")
    (POLICIES / "index.json").write_text(json.dumps(REGISTRY, indent=2) + "\n")
    print("wrote backend/policies/index.json")
