import { useEffect, useState } from "react";
import { CaseSummary, listCases, pollInbox, runReviews } from "../api";
import { Badge } from "../components/Badge";
import { MK } from "../components/MK";

const STATUSES = ["", "Received", "Incomplete", "ReadyForReview", "Pended", "Approved", "Denied", "Synced"];
const TIERS = ["", "likely_approve", "needs_review", "likely_deny"];

const CHANNEL: Record<string, string> = { fax: "Fax", portal: "Provider portal", upload: "Provider upload" };

type SortKey = "id" | "doc_id" | "source" | "description" | "status" | "tier" | "received_at";
const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "id", label: "#" }, { key: "doc_id", label: "Document ID" }, { key: "source", label: "Channel" }, { key: "description", label: "Description" },
  { key: "status", label: "Status" },
  { key: "tier", label: "AI tier" }, { key: "received_at", label: "Received" },
];
const ORDER: Record<string, string[]> = {
  status: STATUSES.slice(1),               // workflow order, not alphabetical
  tier: TIERS.slice(1),
};

export function sortCases(rows: CaseSummary[], key: SortKey, dir: 1 | -1): CaseSummary[] {
  const rank = (c: CaseSummary): number | string => {
    const v = c[key];
    if (ORDER[key]) { const i = ORDER[key].indexOf(String(v ?? "")); return i === -1 ? 99 : i; }
    return v ?? "";
  };
  return [...rows].sort((a, b) => {
    const x = rank(a), y = rank(b);
    return (x < y ? -1 : x > y ? 1 : 0) * dir || (a.id - b.id);
  });
}

export function Queue({ onOpen, onChange, refreshKey }:
  { onOpen: (id: number) => void; onChange: () => void; refreshKey: number }) {
  const [status, setStatus] = useState("");
  const [tier, setTier] = useState("");
  const [rows, setRows] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "received_at", dir: -1 });
  const toggle = (key: SortKey) => setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : 1 }));

  useEffect(() => {
    setRows(null);
    listCases(status || undefined, tier || undefined).then(setRows).catch((e) => setError(e.message));
  }, [status, tier, refreshKey]);

  const [busy, setBusy] = useState<string | null>(null);
  const newCount = rows?.filter((c) => c.status === "Received").length ?? 0;

  async function poll() {
    setBusy("Checking inbox and reviewing (AI-MK)…"); setError(null);
    try {
      const r = await pollInbox();
      const s = r.summary;
      setNote(s ? `${r.created} new case(s). Reviewed ${s.reviewed} (${s.engine === "AI-MK" ? "AI-MK" : s.engine}): ${s.incomplete.length} incomplete, ` +
        `${Object.values(s.ready_by_tier).reduce((a, b) => a + b, 0)} ready for review.` : `${r.created} new case(s).`);
      onChange();
    } catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  }
  async function review() {
    setBusy("Reviewing (AI-MK)…"); setError(null);
    try { const s = await runReviews(); setNote(`Reviewed ${s.reviewed} case(s) (${s.engine === "AI-MK" ? "AI-MK" : s.engine}).`); onChange(); }
    catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  }

  return (
    <section>
      <div className="toolbar">
        <h2>Case queue</h2>
        <label>Status <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s || "All"}</option>)}</select></label>
        <label>AI tier <select value={tier} onChange={(e) => setTier(e.target.value)}>
          {TIERS.map((t) => <option key={t} value={t}>{t ? t.replace(/_/g, " ") : "All"}</option>)}</select></label>
        <button onClick={poll} data-tour="check-inbox" disabled={!!busy}>Check inbox</button>
        <button onClick={review} data-tour="run-reviews" className="theme-btn" disabled={!!busy || newCount === 0}>
          Run AI review ({newCount} new)</button>
      </div>
      {busy && <p className="muted">{busy}</p>}
      {note && !busy && <p className="muted">{note}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {!rows && !error && <p>Loading cases…</p>}
      {rows && rows.length === 0 && <p className="muted">No cases. Drop faxes in the inbox and click “Check inbox”.</p>}
      {rows && rows.length > 0 && (
        <div className="table-wrap" data-tour="case-table"><table>
          <thead><tr>{COLUMNS.map((col) => (
            <th key={col.key} aria-sort={sort.key === col.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
              <button type="button" className="sort" onClick={() => toggle(col.key)}>
                {col.label}{col.key === "tier" && <> <MK /></>} <span className="sort-arrow">{sort.key === col.key ? (sort.dir === 1 ? "▲" : "▼") : "↕"}</span>
              </button></th>))}</tr></thead>
          <tbody>{sortCases(rows, sort.key, sort.dir).map((c) => (
            <tr key={c.id} onClick={() => onOpen(c.id)} className="clickable">
              <td>{c.id}</td><td className="mono">{c.doc_id}</td><td>{CHANNEL[c.source] ?? c.source}</td><td>{c.description}</td><td><Badge kind="status" value={c.status} /></td>
              <td><Badge kind="tier" value={c.tier} /></td><td>{new Date(c.received_at + "Z").toLocaleString()}</td>
            </tr>))}</tbody>
        </table></div>
      )}
    </section>
  );
}
