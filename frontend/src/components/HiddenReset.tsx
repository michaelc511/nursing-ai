import { useState } from "react";
import { resetDemo } from "../api";

// Presenter-only: an invisible click area right after the "Now" title.
// Opens a confirm popup; resets the demo (DEMO_MODE only on the server).
export function HiddenReset() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true); setError(null);
    try {
      await resetDemo();
      try { sessionStorage.removeItem("nurseopsnow.helpchat"); } catch { /* ignore */ }
      location.reload();
    } catch (e) { setError((e as Error).message); setBusy(false); }
  }

  return (
    <>
      <span className="hidden-reset" role="button" tabIndex={-1} aria-label="Reset demo" onClick={() => setOpen(true)} />
      {open && (
        <div className="modal-bg" onClick={() => !busy && setOpen(false)}>
          <div className="card modal" role="dialog" aria-label="Reset demo" onClick={(e) => e.stopPropagation()}>
            <h3>Reset the demo?</h3>
            <p>This deletes every case, decision and audit entry, and puts the 3 sample faxes back in the inbox. Logins stay the same.</p>
            {error && <p role="alert" className="error">{error}</p>}
            <div className="tour-nav">
              <button type="button" className="theme-btn" disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
              <button type="button" className="danger" disabled={busy} onClick={confirm}>{busy ? "Resetting…" : "Yes, reset"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
