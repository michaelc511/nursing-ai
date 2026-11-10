import { render, screen } from "@testing-library/react";
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
  fireEvent.click(screen.getByRole("button", { name: "💬 Guide Me" }));
  fireEvent.click(screen.getByRole("button", { name: "Rules" }));
  expect(screen.getByText(/AI never decides/)).toBeTruthy();
});

test("guide follows the workflow and the signed-in role", async () => {
  const { nextStep } = await import("./guide");
  const c = (id: number, filename: string, status: string) =>
    ({ id, doc_id: `FAX-${id}`, description: "", filename, status, source: "fax", tier: null, received_at: "", status_changed_at: "", sync_status: null });
  const fresh = [c(1, "72148_a_complete.pdf", "Received"), c(2, "73721_b_missing_pt.pdf", "Received")];
  expect(nextStep(undefined, null, null).target).toBe("login");
  expect(nextStep("intake", [], null).target).toBe("check-inbox");
  expect(nextStep("nurse", fresh, null).nextLogin).toBe("intake1");
  expect(nextStep("intake", fresh, null).text).toMatch(/Open case #1/);
  expect(nextStep("intake", fresh, 2).text).toMatch(/Missing info/);
  const ready = [c(1, "72148_a_complete.pdf", "ReadyForReview"), c(2, "73721_b_missing_pt.pdf", "Incomplete")];
  expect(nextStep("intake", ready, null).nextLogin).toBe("nurse1");
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
    ({ id, doc_id: `FAX-${id}`, description: filename, filename, status, tier: null, source: "fax", received_at, status_changed_at: "", sync_status: null });
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
