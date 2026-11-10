import { FormEvent, useEffect, useState } from "react";
import { addDocuments, CaseDetail as Detail, decide, demoPassword, documentUrl, downloadDocument, downloadPolicy, getCase, getSession, policyUrl, simulateCheck } from "../api";
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
  const [demo, setDemo] = useState(false);
  useEffect(() => { demoPassword().then((p) => setDemo(p !== null)); }, []);

  async function check(result: "ready" | "incomplete") {
    setBusy(true); setError(null);
    try { await simulateCheck(id, result); await load(); onChange(); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
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
          {demo && c.status === "Received" && (
            <div className="card" data-tour="demo-check">
              <h3>Simulated AI check (demo)</h3>
              <p className="muted">Claude will do this check in the next phase. For now, pick the result:</p>
              <div className="choices">
                <button type="button" disabled={busy} onClick={() => check("ready")}>Check passed</button>
                <button type="button" className="theme-btn" disabled={busy} onClick={() => check("incomplete")}>Missing info</button>
              </div>
            </div>)}
          <div className="card">
            <h3>AI review</h3>
            {c.ai_review ? <pre>{JSON.stringify(c.ai_review, null, 2)}</pre>
              : <p className="muted">No AI review yet (added in Phase 3). The Nurse decides either way.</p>}
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
