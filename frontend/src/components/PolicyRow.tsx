import { useEffect, useState } from "react";
import { downloadPolicy, listPolicies, Policy, policyUrl } from "../api";

// Home page: all medical policies in one row, each with View (popup) and Download.
export function PolicyRow() {
  const [rows, setRows] = useState<Policy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Policy | null>(null);
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => { listPolicies().then(setRows).catch((e) => setError(e.message)); }, []);
  useEffect(() => {
    let u: string | null = null;
    setUrl(null);
    if (open) policyUrl(open.cpt).then((x) => { u = x; setUrl(x); }).catch((e) => setError(e.message));
    return () => { if (u) URL.revokeObjectURL(u); };
  }, [open]);

  if (error) return <p role="alert" className="error">{error}</p>;
  if (!rows) return <p className="muted">Loading policies…</p>;
  if (rows.length === 0) return null;
  return (
    <section aria-label="Medical policies" data-tour="policies">
      <h3 className="row-title">Medical policies</h3>
      <div className="policy-row">
        {rows.map((p) => (
          <div key={p.cpt} className="card policy-card">
            <div><b>{p.title}</b><br /><span className="muted small">CPT {p.cpt} · v{p.version} · eff. {p.effective}</span></div>
            <div className="policy-actions">
              <button type="button" className="theme-btn" onClick={() => setOpen(p)}>View</button>
              <button type="button" className="theme-btn" onClick={() => downloadPolicy(p)}>Download</button>
            </div>
          </div>))}
      </div>
      {open && (
        <div className="modal-bg" onClick={() => setOpen(null)}>
          <div className="card modal policy-modal" role="dialog" aria-label={`Policy: ${open.title}`} onClick={(e) => e.stopPropagation()}>
            <div className="toolbar"><h3>{open.title} · {open.number} v{open.version}</h3>
              <button type="button" className="theme-btn" onClick={() => downloadPolicy(open)}>Download</button>
              <button type="button" className="link" onClick={() => setOpen(null)}>Close</button></div>
            {url ? <>
              <a className="open-pdf" href={url} target="_blank" rel="noreferrer">Open full PDF ↗</a>
              <iframe title="Policy document" src={url} /></> : <p>Loading policy…</p>}
          </div>
        </div>)}
    </section>
  );
}
