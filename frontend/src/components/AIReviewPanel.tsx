import { AIReview, Evidence } from "../api";
import { Badge } from "./Badge";
import { MK } from "./MK";

// Shows the AI review. Anything from the mock engine is labeled (AI-MK) in the wording.
const RESULT: Record<string, string> = { met: "Met", not_met: "Not met", unclear: "Unclear" };
const docName = (e: Evidence) => (e.doc ? `added document ${e.doc}` : "request");

function Quote({ e, where }: { e: Evidence; where: string }) {
  return (
    <blockquote className="quote">
      “{e.quote}” <span className="muted small">— {where}, page {e.page}
        {e.verified === true ? " · ✓ found in PDF" : e.verified === false ? " · ⚠ not found in PDF" : ""}</span>
    </blockquote>
  );
}

export function AIReviewPanel({ r, label }: { r: AIReview; label: string }) {
  const mocked = label === "AI-MK";
  const tag = mocked ? "(AI-MK)" : "(AI)";
  const f = r.fields || {};
  return (
    <div className="ai-review">
      {mocked && <p className="mk-note"><MK long /> This whole review is a prepared, simulated answer for the demo, not a real AI reading.</p>}
      <p className="ai-summary">{!mocked && <MK />} <b>Summary {tag}:</b> {r.summary}</p>
      <p><Badge kind="tier" value={r.tier} /> <span className="muted small">suggested tier {tag} — a suggestion only; people decide</span></p>
      {r.warnings?.length > 0 && (
        <div className="ai-warn" role="alert"><b>Code checks flagged this review:</b>
          <ul>{r.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>)}

      <h4>Read from the form {tag}</h4>
      <dl className="fields">
        {[["Member", `${f.member_name ?? "—"} · ${f.member_id ?? ""}`], ["Provider", `${f.provider_name ?? "—"} · NPI ${f.provider_npi ?? "—"}`],
          ["Service", `${f.service ?? "—"} (CPT ${f.cpt ?? "—"})`], ["Diagnosis", `${f.diagnosis ?? "—"} (${f.icd10 ?? "—"})`],
          ["Urgency", f.urgency ?? "—"]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
      </dl>

      <h4>Completeness {tag}</h4>
      <ul className="checklist">
        {r.documents_found?.map((d) => <li key={d.name}>✓ {d.name} <span className="muted small">({d.doc ? `added document ${d.doc}` : "request"}, page {d.page})</span></li>)}
        {r.missing?.map((m) => <li key={m.item} className="missing">✗ <b>Missing:</b> {m.item} <span className="muted small">— {m.why}</span></li>)}
      </ul>
      {r.draft_provider_request && (
        <div className="draft"><h4>Provider request drafted {tag}</h4><p>{r.draft_provider_request}</p>
          <span className="muted small">Sent through the (mock) provider notifier; see the audit log.</span></div>)}

      {r.retrieved_criteria?.length > 0 && (<>
        <h4>Policy criteria used {tag}</h4>
        <ul className="retrieved">{r.retrieved_criteria.map((c) => <li key={c.text}><span className="muted small">policy page {c.page}:</span> {c.text}</li>)}</ul>
      </>)}

      {r.criteria?.length > 0 && (<>
        <h4>Criteria check {tag}</h4>
        {r.criteria.map((c) => (
          <div key={c.criterion} className={`criterion crit-${c.result}`}>
            <div><span className={`crit-badge crit-${c.result}`}>{RESULT[c.result]}</span> <b>{c.criterion}</b></div>
            {c.request_evidence.map((e) => <Quote key={e.quote} e={e} where={docName(e)} />)}
            {c.policy_evidence && <Quote e={c.policy_evidence} where="policy" />}
          </div>))}
      </>)}
    </div>
  );
}
