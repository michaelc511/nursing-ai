import { useEffect, useState } from "react";
import { getMetrics, Metrics } from "../api";

const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`);

export function MetricsHeader({ refreshKey }: { refreshKey: number }) {
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getMetrics().then(setM).catch((e) => setError(e.message)); }, [refreshKey]);
  if (error) return <div className="metrics" role="alert">{error}</div>;
  if (!m) return <div className="metrics">Loading metrics…</div>;
  return (
    <div className="metrics" aria-label="Success metrics">
      <div><b>{m.avg_turnaround_days ?? "—"}</b><span>avg turnaround (days)</span></div>
      <div><b>{pct(m.rework_rate)}</b><span>rework (Incomplete)</span></div>
      <div><b>{m.cases_reviewed}</b><span>cases reviewed</span></div>
      <div><b>{pct(m.override_rate)}</b><span>Nurse override of AI</span></div>
      <div><b>{m.total_cases}</b><span>total cases</span></div>
    </div>
  );
}
