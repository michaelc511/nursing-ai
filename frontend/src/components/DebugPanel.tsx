import { useEffect, useState } from "react";
import { AIReview, aiQuality, aiTraces, aiUsage, Quality, TraceRow, Usage } from "../api";
import { useAIMode } from "./MK";

// Not for nurses: shown only when the server runs with DEBUG_UI=true.
// Tokens, cost and latency (F6), the trace of the last runs (F9), raw chunk scores (F18/F10),
// the rewritten query (S8) and quality alerts (N4).
export function DebugPanel({ caseId, review, refreshKey = 0 }: { caseId: number; review: AIReview | null; refreshKey?: number }) {
  const mode = useAIMode();
  const [usage, setUsage] = useState<Usage | null>(null);
  const [traces, setTraces] = useState<TraceRow[]>([]);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (!mode?.debug) return;
    Promise.all([aiUsage(caseId), aiTraces(caseId), aiQuality()])
      .then(([u, t, q]) => { setUsage(u); setTraces(t); setQuality(q); setErr(""); })
      .catch((e) => setErr(String(e.message ?? e)));
  }, [mode?.debug, caseId, refreshKey]);
  if (!mode?.debug) return null;
  const p = review?.pipeline;
  return (
    <details className="debug card" open>
      <summary><b>Debug</b> <span className="muted small">(DEBUG_UI: not shown to nurses)</span></summary>
      {err && <p className="ai-warn">{err}</p>}
      {usage && <p className="small">This case: <b>{usage.calls}</b> AI calls · {usage.input_tokens.toLocaleString()} in /
        {" "}{usage.output_tokens.toLocaleString()} out tokens · <b>${usage.cost_usd.toFixed(4)}</b> · avg {usage.avg_latency_ms} ms</p>}
      {p && <p className="small">Pipeline <code>{p.name}</code>: {p.steps.map((s) => `${s.node} ${s.ms}ms`).join(" → ")}</p>}
      {p?.rewritten_query && <p className="small">Rewritten search query (S8): <i>{p.rewritten_query}</i></p>}
      {review?.policy_chunks?.length ? (
        <table className="small"><thead><tr><th>Chunk</th><th>Vector</th><th>Re-rank</th></tr></thead>
          <tbody>{review.policy_chunks.map((c) => (
            <tr key={c.id}><td>{c.label} p{c.page}</td><td>{c.score?.toFixed(3) ?? "—"}</td><td>{c.rerank?.toFixed(2) ?? "—"}</td></tr>))}
          </tbody></table>) : null}
      {traces.length > 0 && <>
        <p className="small"><b>Last runs</b></p>
        <ul className="small">{traces.slice(0, 5).map((t) => (
          <li key={t.id}>{t.kind} · {t.engine} · {t.total_ms} ms · {t.llm_calls} calls · ${t.cost_usd.toFixed(4)} · {t.outcome}</li>))}</ul>
      </>}
      {quality && <p className="small">Today ${quality.cost_today_usd.toFixed(2)} of ${quality.daily_cap_usd} cap ·
        {" "}👍 {quality.thumbs_up} 👎 {quality.thumbs_down} · override {(quality.override_rate * 100).toFixed(0)}%
        {quality.alerts.map((a) => <span key={a} className="ai-warn"> ⚠ {a}</span>)}</p>}
    </details>
  );
}
