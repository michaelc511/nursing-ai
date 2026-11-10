import { useEffect, useState } from "react";
import { lastRun, RunSummary } from "../api";
import { MK } from "./MK";

// Preview of what Cowork will report after each scheduled run (same run_all service).
export function LastRun({ refreshKey }: { refreshKey: number }) {
  const [s, setS] = useState<RunSummary | null | undefined>(undefined);
  useEffect(() => { lastRun().then(setS).catch(() => setS(null)); }, [refreshKey]);
  if (!s) return null;
  const ready = Object.entries(s.ready_by_tier).map(([t, n]) => `${n} ${t.replace(/_/g, " ")}`).join(", ") || "none";
  return (
    <section className="card lastrun" aria-label="Last automated run">
      <div className="toolbar"><h3>Last run · Cowork preview {s.engine === "AI-MK" ? <MK /> : `(${s.engine})`}</h3>
        <span className="muted small">{s.at ? new Date(s.at + "Z").toLocaleString() : ""} · {s.trigger}</span></div>
      <p>{s.new} new · {s.reviewed} reviewed · {s.incomplete.length} incomplete
        {s.incomplete.length > 0 && <> ({s.incomplete.map((i) => `#${i.id} ${i.missing}`).join("; ")}, provider asked)</>}
        {" "}· ready for review: {ready} · {s.stuck} stuck over 2 days</p>
    </section>
  );
}
