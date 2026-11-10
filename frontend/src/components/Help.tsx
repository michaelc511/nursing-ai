import { useEffect, useState } from "react";
import { startTour } from "./HelpChat";

export type Screen = "login" | "queue" | "case";

export const STEPS: Record<Screen, { title: string; steps: string[] }> = {
  login: { title: "Sign in", steps: [
    "Pick a user: nurse1 / nurse2 (Nurse), meddir (Medical Director), intake1 (Intake Coordinator).",
    "The demo password is filled in. Click Sign in.",
  ]},
  queue: { title: "Case queue", steps: [
    "Click Check inbox to turn new faxes into cases.",
    "Filter by Status or AI tier.",
    "Click a row to open the case. Medical policies (row below the queue): View or Download each one.",
    "Top cards show turnaround, rework, cases reviewed and override rate.",
  ]},
  case: { title: "Case detail", steps: [
    "Read the request on the left; the Policy tab shows the criteria. Download saves either PDF (request downloads are logged in the audit log).",
    "Ready or Pended: Approve or Pend (only the Medical Director can Deny), add a rationale, Submit.",
    "Incomplete: Add documents (e.g. missing PT notes) to send it back to Received.",
    "Only Nurses and Medical Directors can decide. AI never decides.",
    "The audit log shows who did what. Back to queue returns to the list.",
  ]},
};

// Workflow order: who does what (roles from README "How to use").
export const WORKFLOW: { who: string; role: string | null; does: string }[] = [
  { who: "Intake Coordinator · intake1", role: "intake", does: "Check inbox: each new fax becomes a case (Received)." },
  { who: "AI check · for now the Intake Coordinator clicks Simulated AI check", role: null, does: "Received → Ready for review, or Incomplete (the provider is asked for what's missing)." },
  { who: "Intake Coordinator · intake1", role: "intake", does: "Incomplete: Add documents when the provider replies → back to Received → AI review again." },
  { who: "Nurse · nurse1, nurse2", role: "nurse", does: "Ready: read the request and the policy, then Approve, or Pend for the Medical Director if it doesn't meet the policy." },
  { who: "Medical Director · meddir", role: "medical_director", does: "Decides Pended cases and is the only one who can Deny (can also decide any Ready case)." },
  { who: "System", role: null, does: "Approved or Denied → sent to UM, provider notified → Synced." },
  { who: "Everyone", role: null, does: "Audit log shows who did what; top cards track turnaround and rework." },
];

export const ABOUT = [
  "What it is: a prototype for a regional health plan that gets ~15,000 prior authorization requests a month. Today turnaround is 4.2 days and 22% of requests need rework because information is missing.",
  "Goal: cut turnaround by about 40% with no extra staff, while keeping clinical quality and compliance.",
  "How it helps: requests are checked for missing documents at intake, the provider is asked right away, and (from Phase 3) Claude prepares a cited summary against the MRI policy.",
  "Who decides: only a Nurse or Medical Director approves or denies. AI never decides. Every action is in the audit log.",
  "Data: all faxes and patients are synthetic. No real patient information.",
];

export function HelpButton({ screen, role }: { screen: Screen; role?: string }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const h = STEPS[screen];
  return (
    <>
      <button type="button" className="help-btn" aria-label="Help" onClick={() => setOpen(true)}>?</button>
      {open && (
        <div className="modal-bg" onClick={() => setOpen(false)}>
          <div className="card modal" role="dialog" aria-label={`Help: ${h.title}`} onClick={(e) => e.stopPropagation()}>
            <h3>About NurseOps Now</h3>
            <ul className="about">{ABOUT.map((a) => <li key={a}>{a}</li>)}</ul>
            <h3>This screen: {h.title}</h3>
            <ol>{h.steps.map((s) => <li key={s}>{s}</li>)}</ol>
            <h3>Workflow: who does what</h3>
            <ol className="workflow">{WORKFLOW.map((w) => (
              <li key={w.who + w.does} className={role && w.role === role ? "mine" : undefined}>
                <b>{w.who}</b>{role && w.role === role && <span className="you"> (you)</span>}<br />{w.does}</li>))}</ol>
            <div className="tour-nav">
              <button type="button" className="theme-btn" onClick={() => { setOpen(false); startTour(); }}>Guide Me</button>
              <button type="button" onClick={() => setOpen(false)}>Got it</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
