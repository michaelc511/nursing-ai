import { useState } from "react";
import { sendFeedback } from "../api";

// N4 online quality: thumbs up/down on an AI review or an AI Assist answer (audited; feeds the quality page).
export function Feedback({ kind, caseId, question }: { kind: "review" | "assist"; caseId: number | null; question?: string }) {
  const [state, setState] = useState<"idle" | "sent" | "error">("idle");
  const rate = (r: 1 | -1) => sendFeedback(kind, caseId, r, question).then(() => setState("sent")).catch(() => setState("error"));
  if (state === "sent") return <span className="muted small feedback">Thanks, noted.</span>;
  return (
    <span className="feedback small" aria-label="Was this helpful?">
      <span className="muted">Helpful?</span>
      <button type="button" className="link" aria-label="Helpful" onClick={() => rate(1)}>👍</button>
      <button type="button" className="link" aria-label="Not helpful" onClick={() => rate(-1)}>👎</button>
      {state === "error" && <span className="muted"> could not send</span>}
    </span>
  );
}
