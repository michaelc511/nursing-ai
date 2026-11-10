import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { Badge } from "./components/Badge";

test("shows the login screen when signed out", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "NurseOps Now" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
});

test("badge formats tiers", () => {
  render(<Badge kind="tier" value="likely_approve" />);
  expect(screen.getByText("likely approve")).toBeTruthy();
});

test("help popup opens with steps for the screen", async () => {
  const { HelpButton } = await import("./components/Help");
  const { fireEvent } = await import("@testing-library/react");
  render(<HelpButton screen="queue" role="nurse" />);
  fireEvent.click(screen.getByRole("button", { name: "Help" }));
  expect(screen.getByRole("dialog", { name: "Help: Case queue" })).toBeTruthy();
  expect(screen.getByText("Workflow: who does what")).toBeTruthy();
  expect(screen.getByText("(you)")).toBeTruthy();
  expect(screen.getByText("About NurseOps Now")).toBeTruthy();
});

test("help chat answers topics", async () => {
  const { HelpChat } = await import("./components/HelpChat");
  const { fireEvent } = await import("@testing-library/react");
  render(<HelpChat screen="queue" role="nurse" />);
  fireEvent.click(screen.getByRole("button", { name: /AI Assist/ }));
  fireEvent.click(screen.getByRole("button", { name: "Rules" }));
  expect(screen.getByText(/AI never decides/)).toBeTruthy();
});

test("guide follows the workflow and the signed-in role", async () => {
  const { nextStep } = await import("./guide");
  const c = (id: number, filename: string, status: string) =>
    ({ id, doc_id: `FAX-${id}`, description: "", filename, status, source: "fax", tier: null, ai_engine: null, received_at: "", status_changed_at: "", sync_status: null });
  const fresh = [c(1, "72148_a_complete.pdf", "Received"), c(2, "73721_b_missing_pt.pdf", "Received")];
  expect(nextStep(undefined, null, null).target).toBe("login");
  expect(nextStep("intake", [], null).target).toBe("check-inbox");
  expect(nextStep("nurse", fresh, null).nextLogin).toBe("intake1");
  expect(nextStep("intake", fresh, null).target).toBe("run-reviews");
  expect(nextStep("intake", fresh, null).text).toMatch(/AI-MK/);
  const ready = [c(1, "72148_a_complete.pdf", "ReadyForReview"), c(2, "73721_b_missing_pt.pdf", "Incomplete")];
  expect(nextStep("intake", ready, null).nextLogin).toBe("nurse1");
  expect(nextStep("nurse", ready, 1).text).toMatch(/AI review \(AI-MK\)/);
  expect(nextStep("nurse", ready, 1).text).toMatch(/Approve it/);
  const pended = [c(3, "70551_c_not_met.pdf", "Pended")];
  expect(nextStep("nurse", pended, null).nextLogin).toBe("meddir");
  const docs = [c(2, "73721_b_missing_pt.pdf", "Incomplete")];
  expect(nextStep("intake", docs, 2).target).toBe("add-docs");
  expect(nextStep("nurse", [c(1, "x.pdf", "Synced")], null).target).toBe("metrics");
});

test("intro tells each role what to do", async () => {
  const { Intro } = await import("./components/Intro");
  render(<Intro role="intake" />);
  expect(screen.getByText(/click Check inbox/)).toBeTruthy();
});

test("defaults to the white/red theme and toggles dark mode", async () => {
  const { ThemeToggle } = await import("./components/ThemeToggle");
  const { fireEvent } = await import("@testing-library/react");
  try { window.localStorage?.clear(); } catch { /* storage unavailable in this test env */ }
  render(<ThemeToggle />);
  expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  fireEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
  expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
});

test("hidden reset asks for confirmation", async () => {
  const { HiddenReset } = await import("./components/HiddenReset");
  const { fireEvent } = await import("@testing-library/react");
  render(<HiddenReset />);
  fireEvent.click(screen.getByLabelText("Reset demo"));
  expect(screen.getByText("Reset the demo?")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByText("Reset the demo?")).toBeNull();
});

test("unit board shows today's date and notices", async () => {
  const { Notices } = await import("./components/Notices");
  render(<Notices today={new Date(2026, 10, 10)} />);
  expect(screen.getByText(/Unit board/)).toBeTruthy();
  expect(screen.getByText("Shift change")).toBeTruthy();
  expect(screen.getByText("Policy")).toBeTruthy();
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
});

test("queue sorts by column, status in workflow order", async () => {
  const { sortCases } = await import("./pages/Queue");
  const c = (id: number, filename: string, status: string, received_at: string) =>
    ({ id, doc_id: `FAX-${id}`, description: filename, filename, status, tier: null, ai_engine: null, source: "fax", received_at, status_changed_at: "", sync_status: null });
  const rows = [c(1, "b.pdf", "Synced", "2026-11-10T09:00"), c(2, "a.pdf", "Received", "2026-11-10T08:00"),
                c(3, "c.pdf", "ReadyForReview", "2026-11-10T10:00")];
  expect(sortCases(rows, "status", 1).map((r) => r.id)).toEqual([2, 3, 1]);
  expect(sortCases(rows, "description", -1).map((r) => r.id)).toEqual([3, 1, 2]);
  expect(sortCases(rows, "received_at", -1).map((r) => r.id)).toEqual([3, 1, 2]);
});

test("home page policy row lists policies with view and download", async () => {
  const { PolicyRow } = await import("./components/PolicyRow");
  const rows = [{ cpt: "73721", title: "MRI knee", number: "RHP-IMG-022", version: "2.1", effective: "2026-04-01" }];
  globalThis.fetch = (async () => new Response(JSON.stringify(rows), { status: 200 })) as typeof fetch;
  render(<PolicyRow />);
  expect(await screen.findByText("MRI knee")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Download" })).toBeTruthy();
});

test("AI review panel labels everything (AI-MK) and shows evidence", async () => {
  const { AIReviewPanel } = await import("./components/AIReviewPanel");
  const r = { engine: "AI-MK", fields: { cpt: "73721", diagnosis: "Knee pain", icd10: "M25.561" }, complete: false,
    documents_found: [{ name: "Request form", doc: 0, page: 1 }], missing: [{ item: "PT notes", why: "policy needs 4–6 weeks" }],
    retrieved_criteria: [], tier: "needs_review", summary: "Incomplete.", warnings: [],
    draft_provider_request: "Please send PT notes.",
    criteria: [{ criterion: "X-ray done", result: "met" as const, request_evidence: [{ quote: "Right knee X-ray", doc: 0, page: 2, verified: true }], policy_evidence: null }] };
  render(<AIReviewPanel r={r} label="AI-MK" />);
  expect(screen.getByText(/Summary \(AI-MK\)/)).toBeTruthy();
  expect(screen.getByText(/not a real AI reading/)).toBeTruthy();
  expect(screen.getByText("Provider request drafted (AI-MK)")).toBeTruthy();
  expect(screen.getByText(/found in PDF/)).toBeTruthy();
  expect(screen.getByText(/Missing:/).closest("li")?.textContent).toMatch(/PT notes/);
});

test("mock banner says AI-MK is not real AI", async () => {
  const { MockBanner } = await import("./components/MK");
  render(<MockBanner />);
  expect(await screen.findByText(/Mock AI mode/)).toBeTruthy();
  expect(screen.getByText(/not real AI/)).toBeTruthy();
});

test("real AI mode shows the AI icon instead of AI-MK", async () => {
  const api = await import("./api");
  const { MK } = await import("./components/MK");
  const spy = (await import("vitest")).vi.spyOn(api, "aiMode").mockResolvedValue({ mode: "claude", label: "AI" });
  render(<MK />);
  expect(await screen.findByRole("img", { name: /Generated by AI/ })).toBeTruthy();
  expect(screen.queryByText(/AI-MK/)).toBeNull();
  spy.mockRestore();
});

test("icon preview is ignored outside demo mode", async () => {
  const api = await import("./api");
  const { MK } = await import("./components/MK");
  const { vi } = await import("vitest");
  const spy = vi.spyOn(api, "aiMode").mockResolvedValue({ mode: "mock", label: "AI-MK", demo: false });
  window.history.pushState({}, "", "/?icons=ai");
  render(<MK />);
  expect(await screen.findByText("AI-MK")).toBeTruthy();
  window.history.pushState({}, "", "/");
  spy.mockRestore();
});

async function renderFooter(mode: object) {
  const api = await import("./api");
  const { DemoFooter } = await import("./components/DemoFooter");
  const { DebugBanner } = await import("./components/DebugMode");
  const { vi } = await import("vitest");
  const { act } = await import("@testing-library/react");
  sessionStorage.clear();
  const modeSpy = vi.spyOn(api, "aiMode").mockResolvedValue({ label: "AI-MK", ...mode } as never);
  const setSpy = vi.spyOn(api, "setAIMode").mockResolvedValue({ mode: "claude" });
  render(<><DebugBanner /><DemoFooter /></>);
  await act(async () => { await Promise.resolve(); });
  return { setSpy, restore: () => { modeSpy.mockRestore(); setSpy.mockRestore(); } };
}

test("Synthetic data only is an invisible AI switch in demo mode", async () => {
  const { setSpy, restore } = await renderFooter({ mode: "mock", demo: true, switchable: true, claude_available: true });
  expect(screen.queryByRole("button")).toBeNull();
  fireEvent.click(screen.getByText("Synthetic data only"));
  expect(setSpy).toHaveBeenCalledWith("claude");
  restore();
});

test("the hidden AI switch says so when Claude isn't connected", async () => {
  const { setSpy, restore } = await renderFooter({ mode: "mock", demo: true, switchable: true, claude_available: false });
  fireEvent.click(screen.getByText("Synthetic data only"));
  expect(setSpy).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toMatch(/not connected/);
  restore();
});

test("Medical Directors toggles debug mode and a banner announces it", async () => {
  const { restore } = await renderFooter({ mode: "claude", demo: true, switchable: true, claude_available: true });
  expect(screen.queryByText(/Debug mode on/)).toBeNull();
  fireEvent.click(screen.getByText("Medical Directors"));
  expect(await screen.findByText(/Debug mode on/)).toBeTruthy();
  fireEvent.click(screen.getByText("Medical Directors"));
  await waitFor(() => expect(screen.queryByText(/Debug mode on/)).toBeNull());
  restore();
});

test("the hidden switches do nothing outside demo mode", async () => {
  const { setSpy, restore } = await renderFooter({ mode: "claude", demo: false, switchable: false });
  fireEvent.click(screen.getByText("Synthetic data only"));
  fireEvent.click(screen.getByText("Medical Directors"));
  expect(setSpy).not.toHaveBeenCalled();
  expect(screen.queryByText(/Debug mode on/)).toBeNull();
  restore();
});

// ---------------------------------------------------------------- Phase 10
test("typed question goes to AI Assist and shows sources", async () => {
  const { HelpChat } = await import("./components/HelpChat");
  const { fireEvent, waitFor } = await import("@testing-library/react");
  sessionStorage.clear();
  globalThis.fetch = (async (url: string) => {
    if (String(url).includes("/api/assist/chat")) return new Response(JSON.stringify({
      answer: "Case 2 is Incomplete: PT notes are missing.", engine: "AI", blocked: null, rewritten: null,
      tools_used: ["get_case"], sources: [{ type: "case", label: "Case 2 (PRT-20261110-0002)", case_id: 2 }] }), { status: 200 });
    return new Response(JSON.stringify({ mode: "claude", label: "AI" }), { status: 200 });
  }) as typeof fetch;
  render(<HelpChat screen="queue" role="nurse" />);
  fireEvent.click(screen.getByRole("button", { name: /AI Assist/ }));
  fireEvent.change(screen.getByLabelText("Ask a help question"), { target: { value: "What is missing on case 2?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await waitFor(() => expect(screen.getByText(/PT notes are missing/)).toBeTruthy());
  expect(screen.getByText("Case 2 (PRT-20261110-0002)")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Helpful" })).toBeTruthy();
});

test("AI Assist falls back to the built-in guide when the server is down", async () => {
  const { HelpChat } = await import("./components/HelpChat");
  const { fireEvent, waitFor } = await import("@testing-library/react");
  sessionStorage.clear();
  globalThis.fetch = (async () => { throw new TypeError("network"); }) as unknown as typeof fetch;
  render(<HelpChat screen="queue" role="nurse" />);
  fireEvent.click(screen.getByRole("button", { name: /AI Assist/ }));
  fireEvent.change(screen.getByLabelText("Ask a help question"), { target: { value: "what are the rules" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await waitFor(() => expect(screen.getByText(/Can't reach the server/)).toBeTruthy());
  expect(screen.getByText(/AI never decides/)).toBeTruthy();
});

test("review panel lists the policy sections the AI read; debug stays hidden", async () => {
  const { AIReviewPanel } = await import("./components/AIReviewPanel");
  const r = { engine: "AI", fields: {}, documents_found: [], missing: [], complete: true, retrieved_criteria: [],
    criteria: [], tier: "likely_approve", summary: "ok", draft_provider_request: null, warnings: [],
    policy_chunks: [{ id: "72148-v3.2-2.A", label: "§2.A", section_title: "Covered when", page: 1, quote: "Low back pain 6 weeks", score: 0.6 }],
    pipeline: { name: "graph", steps: [{ node: "read_form", ms: 3 }], rewritten_query: "low back pain conservative therapy" } };
  render(<AIReviewPanel r={r as never} label="AI" caseId={1} />);
  expect(screen.getByText(/Policy sections the AI read/)).toBeTruthy();
  expect(screen.getByText(/Low back pain 6 weeks/)).toBeTruthy();
  expect(screen.queryByText(/Rewritten search query/)).toBeNull();
});
