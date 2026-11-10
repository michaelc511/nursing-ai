// Short intro shown on the page. Details live in the ? help popup.
const NEXT: Record<string, string> = {
  intake: "Your job: click Check inbox (the AI reviews each new request) and add documents to Incomplete cases.",
  nurse: "Your job: open a Ready for review case, read the request and policy, then Approve it or Pend it for the Medical Director.",
  medical_director: "Your job: decide Pended cases. Only you can Deny.",
};

export function Intro({ role }: { role?: string }) {
  return (
    <div className="intro" role="note">
      <b>NurseOps Now</b> helps prior authorization nurses review MRI requests faster.
      Faxes come in, get checked, and a Nurse or Medical Director makes every decision.{" "}
      {role ? NEXT[role] : "Sign in as any demo user to start."}{" "}
      <span className="muted">Click <b>?</b> or <b>AI Assist</b> (bottom right) for step-by-step help.</span>
    </div>
  );
}
