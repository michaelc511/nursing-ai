// The only place the UI talks to the backend. Adds the login token to every call.
export type User = { username: string; full_name: string; role: string };
export type CaseSummary = {
  id: number; doc_id: string; description: string; source: string; filename: string; status: string; tier: string | null;
  received_at: string; status_changed_at: string; sync_status: string | null;
};
export type Policy = { cpt: string; title: string; number: string; version: string; effective: string; codes?: string };
export type CaseDetail = CaseSummary & {
  sync_detail: string | null;
  policy: Policy | null;
  extra_documents: string[];
  ai_review: Record<string, unknown> | null;
  decisions: { decision: string; rationale: string; override: boolean; ai_tier: string | null;
               reviewer: string; role: string; at: string }[];
  audit: { actor: string; action: string; details: Record<string, unknown>; at: string }[];
  allowed_actions: string[];
};
export type Metrics = {
  total_cases: number; by_status: Record<string, number>; cases_reviewed: number;
  avg_turnaround_days: number | null; rework_rate: number | null; override_rate: number | null;
};

const KEY = "nurseopsnow.session";

export function getSession(): { token: string; user: User } | null {
  try { const raw = sessionStorage.getItem(KEY); return raw ? JSON.parse(raw) : null; }
  catch { return null; }
}
function setSession(s: { token: string; user: User } | null) {
  try { s ? sessionStorage.setItem(KEY, JSON.stringify(s)) : sessionStorage.removeItem(KEY); }
  catch { /* storage unavailable: session lasts until reload */ }
}

let memorySession = getSession();
export const logout = () => { memorySession = null; setSession(null); };

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (memorySession) headers.set("Authorization", `Bearer ${memorySession.token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401 && memorySession) { logout(); location.reload(); }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function login(username: string, password: string): Promise<User> {
  const r = await call<{ token: string } & User>("/api/auth/login", {
    method: "POST", body: JSON.stringify({ username, password }) });
  const user = { username: r.username, full_name: r.full_name, role: r.role };
  memorySession = { token: r.token, user };
  setSession(memorySession);
  return user;
}

export async function demoPassword(): Promise<string | null> {
  try { const r = await fetch("/api/auth/demo"); return r.ok ? (await r.json()).password : null; }
  catch { return null; }
}

export const listCases = (status?: string, tier?: string) => {
  const q = new URLSearchParams();
  if (status) q.set("status", status);
  if (tier) q.set("tier", tier);
  return call<CaseSummary[]>(`/api/cases?${q}`);
};
export const getCase = (id: number) => call<CaseDetail>(`/api/cases/${id}`);
export const getMetrics = () => call<Metrics>("/api/metrics");
export const pollInbox = () => call<{ created: number[] }>("/api/intake/poll", { method: "POST" });
export const decide = (id: number, action: string, rationale: string) =>
  call<{ status: string; override: boolean }>(`/api/cases/${id}/decision`, {
    method: "POST", body: JSON.stringify({ action, rationale }) });

export const addDocuments = (id: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return call<CaseSummary>(`/api/cases/${id}/documents`, { method: "POST", body: form });
};

export const simulateCheck = (id: number, result: "ready" | "incomplete") =>
  call<{ status: string }>(`/api/demo/cases/${id}/check?result=${result}`, { method: "POST" });

export const resetDemo = () => call<{ inbox: string[] }>("/api/demo/reset", { method: "POST" });

export const listPolicies = () => call<Policy[]>("/api/policies");

async function blobUrl(path: string): Promise<string> {
  const res = await fetch(path, { headers: memorySession ? { Authorization: `Bearer ${memorySession.token}` } : {} });
  if (!res.ok) throw new Error("Could not load document");
  return URL.createObjectURL(await res.blob());
}
export const policyUrl = (cpt: string) => blobUrl(`/api/policies/${cpt}/document`);

/** Download through the authenticated API (the browser can't add the login token to a plain link). */
export async function downloadPolicy(p: Policy) {
  const url = await blobUrl(`/api/policies/${p.cpt}/document?download=true`);
  const a = document.createElement("a");
  a.href = url; a.download = `${p.number}_${p.title.replace(/ /g, "_")}_v${p.version}.pdf`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function downloadDocument(id: number, index: number, filename: string) {
  const url = await blobUrl(`/api/cases/${id}/document?index=${index}&download=true`);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function documentUrl(id: number, index = 0): Promise<string> {
  const res = await fetch(`/api/cases/${id}/document?index=${index}`, {
    headers: memorySession ? { Authorization: `Bearer ${memorySession.token}` } : {} });
  if (!res.ok) throw new Error("Could not load document");
  return URL.createObjectURL(await res.blob());
}
