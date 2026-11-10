export function Badge({ value, kind }: { value: string | null; kind: "status" | "tier" }) {
  if (!value) return <span className="badge muted">—</span>;
  return <span className={`badge ${kind}-${value}`}>{value.replace(/_/g, " ")}</span>;
}
