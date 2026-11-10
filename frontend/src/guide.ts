// "What do I do next?" from the live app: who is signed in + where each case stands.
// Plain words only. Workflow order: intake -> check -> nurse -> medical director -> missing docs -> done.
import { CaseSummary } from "./api";

export type Guide = { who: string; text: string; target?: string; nextLogin?: string };

const LOGIN: Record<string, { login: string; name: string }> = {
  intake: { login: "intake1", name: "Intake Coordinator" },
  nurse: { login: "nurse1", name: "Nurse" },
  medical_director: { login: "meddir", name: "Medical Director" },
};

const ABOUT_CASE: Record<string, { desc: string; decide: string }> = {
  "72148_a_complete.pdf": { desc: "lumbar MRI, complete", decide: "Approve it (8 weeks of PT are documented)" },
  "73721_b_missing_pt.pdf": { desc: "knee MRI, missing PT notes", decide: "Approve it (the PT notes show 6 weeks and the knee still catches)" },
  "70551_c_not_met.pdf": { desc: "brain MRI, no red flags", decide: "Pend it for the Medical Director (headache with no red flags; only the Medical Director can deny)" },
};
const about = (c: CaseSummary) => ABOUT_CASE[c.filename];
const label = (c: CaseSummary) => `case #${c.id} · ${c.doc_id}${about(c) ? ` (${about(c).desc})` : ""}`;

type Stage = { role: "intake" | "nurse" | "medical_director"; cases: CaseSummary[]; kind: string };

function stage(cases: CaseSummary[]): Stage | null {
  const by = (s: string) => cases.filter((c) => c.status === s);
  if (cases.length === 0) return { role: "intake", cases: [], kind: "inbox" };
  if (by("Received").length) return { role: "intake", cases: by("Received"), kind: "check" };
  if (by("ReadyForReview").length) return { role: "nurse", cases: by("ReadyForReview"), kind: "decide" };
  if (by("Pended").length) return { role: "medical_director", cases: by("Pended"), kind: "decide" };
  if (by("Incomplete").length) return { role: "intake", cases: by("Incomplete"), kind: "docs" };
  return null;
}

function canDo(role: string | undefined, need: Stage["role"]) {
  return role === need || (need === "nurse" && role === "medical_director");
}

export function nextStep(role: string | undefined, cases: CaseSummary[] | null, openId: number | null): Guide {
  if (!role) return { who: "Anyone", text: "Pick the user shown in the last step (start with intake1, the Intake Coordinator) and click Sign in.", target: "login" };
  if (!cases) return { who: "You", text: "Loading the cases…" };
  const st = stage(cases);
  if (!st) return { who: "Everyone", text: "All cases are done and sent to the health plan's system. Look at the cards at the top: turnaround, rework, cases reviewed. That's the full workflow!", target: "metrics" };

  const need = LOGIN[st.role];
  if (!canDo(role, st.role)) {
    return { who: `Next: ${need.name} · ${need.login}`, nextLogin: need.login,
      text: `This step is for the ${need.name}. Click Sign out (top right), then sign in as ${need.login}.`, target: "signout" };
  }
  const me = `You · ${LOGIN[role!]?.name ?? role}`;
  if (st.kind === "inbox") return { who: me, text: "Click Check inbox. New requests come in and the AI (AI-MK) reviews each one right away.", target: "check-inbox" };
  if (st.kind === "check") return { who: me, text: `${st.cases.length} case(s) still need an AI review. Click Run AI review on the queue (AI-MK).`, target: "run-reviews" };

  const open = openId === null ? null : cases.find((c) => c.id === openId) ?? null;
  const todo = st.cases[0];
  if (!open || !st.cases.some((c) => c.id === open.id)) {
    const where = open ? "Go back to the queue, then open" : "Open";
    return { who: me, text: `${where} ${label(todo)}.`, target: open ? "back" : "case-table" };
  }
  const a = about(open);
  if (st.kind === "docs") return { who: me,
    text: "The AI review (AI-MK) found the PT notes missing and already asked the provider. When they arrive, click Add documents and pick 73721_b_followup_pt_notes.pdf (in data/samples/followup). The AI reviews it again.", target: "add-docs" };
  const decideText = open.status === "Pended" && role === "medical_director"
    ? "Deny it if it doesn't meet the policy (or Approve it)" : a ? a.decide : "Approve or Pend it";
  return { who: me, text: `Read the AI review (AI-MK): its quotes, the missing items and its suggested tier. Compare with the Policy tab. Then ${decideText}. Pick the choice, write a short reason, and click Submit decision.`, target: "decision" };
}
