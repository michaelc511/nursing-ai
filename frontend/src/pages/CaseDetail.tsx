import { FormEvent, useEffect, useState } from "react";
import { addDocuments, CaseDetail as Detail, decide, documentUrl, downloadDocument, downloadPolicy, getCase, getSession, policyUrl, reviewCase } from "../api";
import { AIReviewPanel } from "../components/AIReviewPanel";
import { MK } from "../components/MK";
import { Badge } from "../components/Badge";
import { roleName } from "../roles";

export function CaseDetail({ id, onBack, onChange }: { id: number; onBack: () => void; onChange: () => void }) {
  const [c, setC] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docIndex, setDocIndex] = useState(0);
  const [docUrl, setDocUrl] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);

  const role = getSession()?.user.role;
  const [reviewing, setReviewing] = useState(false);

  async function runReview() {
    setReviewing(true); setError(null);
    try { await reviewCase(id); await load(); onChange(); }
    catch (err) { setError((err as Error).message); }
    finally { setReviewing(false); }
  }
  const canDecide = role === "nurse" || role === "medical_director";

  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(null);
    try { await addDocuments(id, file); await load(); onChange(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  const load = () => getCase(id).then(setC).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    let url: string | null = null;
    setDocUrl(null);
    const load = docIndex === -1 && c?.policy ? policyUrl(c.policy.cpt) : documentUrl(id, Math.max(docIndex, 0));
    load.then((u) => { url = u; setDocUrl(u); }).catch((e) => setError(e.message));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [id, docIndex, c?.policy?.cpt]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await decide(id, action, rationale); setAction(""); setRationale(""); await load(); onChange(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  if (error && !c) return <p role="alert" className="error">{error}</p>;
  if (!c) return <p>Loading case…</p>;
  const docs = [c.filename, ...c.extra_documents];

  return (
    <section>
      <button className="link" data-tour="back" onClick={onBack}>← Back to queue</button>
      <h2>Case #{c.id} · {c.doc_id}</h2>
      <p className="muted">{c.description} · file {c.filename}</p>
      <p><Badge kind="status" value={c.status} /> <Badge kind="tier" value={c.tier} />
        {c.sync_detail && <span className="muted"> · {c.sync_detail}</span>}</p>
      <div className="detail-grid">
        <div className="card viewer" data-tour="viewer">
          <div className="tabs" role="tablist">
            {docs.map((d, i) => (
              <button key={d + i} type="button" role="tab" aria-selected={docIndex === i}
                className={docIndex === i ? "tab active" : "tab"} onClick={() => setDocIndex(i)}>
                {i === 0 ? "Request" : `Added document ${i}`}</button>))}
            {c.policy && <button type="button" role="tab" aria-selected={docIndex === -1} data-tour="policy-tab"
              className={docIndex === -1 ? "tab active" : "tab"} onClick={() => setDocIndex(-1)}>Policy: {c.policy.title}</button>}
          </div>
          {docIndex >= 0 && (
            <div className="policy-bar">
              <span>{docs[docIndex]}</span>
              <button type="button" className="theme-btn" onClick={() =>
                downloadDocument(id, docIndex, docs[docIndex]).then(() => load()).catch((e) => setError(e.message))}>Download</button>
            </div>)}
          {docIndex === -1 && c.policy && (
            <div className="policy-bar">
              <span>{c.policy.number} · v{c.policy.version} · effective {c.policy.effective}</span>
              <button type="button" className="theme-btn" onClick={() => downloadPolicy(c.policy!)}>Download</button>
            </div>)}
          {docUrl ? <>
            <a className="open-pdf" href={docUrl} target="_blank" rel="noreferrer">Open full PDF ↗</a>
            <iframe title={docIndex === -1 ? "Policy document" : "Case document"} src={docUrl} /></> : <p>Loading document…</p>}
        </div>
        <div>
          <div className="card" data-tour="ai-review">
            <div className="toolbar">
              <h3>AI review <MK busy={reviewing} /></h3>
              <button type="button" data-tour="run-review" className={c.ai_review ? "theme-btn" : undefined}
                disabled={reviewing} onClick={runReview}>
                {reviewing ? "Reviewing…" : c.ai_review ? "Re-run AI review" : "Run AI review"}</button>
            </div>
            {reviewing && <p className="muted"><MK busy /> Reviewing: reading the request, checking it against the policy…</p>}
            {!reviewing && c.ai_review && <>
              <p className="muted small">Reviewed {new Date(c.ai_reviewed_at + "Z").toLocaleString()}</p>
              <AIReviewPanel r={c.ai_review} label={c.ai_label ?? "AI"} />
            </>}
            {!reviewing && !c.ai_review && <p className="muted">No AI review yet. Click Run AI review. The Nurse decides either way.</p>}
          </div>
          <div className="card">
            <h3>Decision</h3>
            <div data-tour="decision">
            {c.status === "Incomplete" && (
              <label className="upload" data-tour="add-docs">Add documents (moves the case back to Received)
                <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" disabled={busy}
                  onChange={(e) => upload(e.target.files?.[0])} /></label>)}
            {!canDecide && c.allowed_actions.length > 0
              ? <p className="muted">Only Nurses and Medical Directors can decide.</p>
              : c.allowed_actions.length === 0
              ? <p className="muted">No decision possible in status {c.status}.</p>
              : <form onSubmit={submit}>
                  <div className="choices">{c.allowed_actions.filter((a) => a !== "Deny" || role === "medical_director").map((a) => (
                    <label key={a}><input type="radio" name="action" value={a} checked={action === a}
                      onChange={() => setAction(a)} required /> {a}</label>))}</div>
                  {role !== "medical_director" && <p className="muted small">Only a Medical Director can deny. If it doesn't meet the policy, Pend it for MD review.</p>}
                  <label>Rationale (required)
                    <textarea value={rationale} onChange={(e) => setRationale(e.target.value)} required rows={3} /></label>
                  {error && <p role="alert" className="error">{error}</p>}
                  <button disabled={busy || !action || !rationale.trim()}>{busy ? "Saving…" : "Submit decision"}</button>
                </form>}
            {c.decisions.map((d, i) => (
              <p key={i} className="muted"><b>{d.decision}</b> by {d.reviewer} ({roleName(d.role)}):
                {" "}{d.rationale}{d.override && " · override of AI tier"}</p>))}
            </div>
          </div>
          <div className="card" data-tour="audit">
            <h3>Audit log</h3>
            <ul className="audit">{c.audit.map((a, i) => (
              <li key={i}><span className="muted">{new Date(a.at + "Z").toLocaleString()}</span> · <b>{a.actor}</b> · {a.action}
                {a.action === "status_change" && <> ({String(a.details.from)} → {String(a.details.to)})</>}</li>))}</ul>
          </div>
        </div>
      </div>
    </section>
  );
}
