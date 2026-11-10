import { useEffect, useState } from "react";
import { aiMode, AIMode, setAIMode } from "../api";

// Demo-mode switch between AI-MK (mocked) and real Claude. Hidden in production (DEMO_MODE off).
export function AISwitch({ signedIn = true }: { signedIn?: boolean }) {
  const [m, setM] = useState<AIMode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { aiMode().then(setM); }, []);
  if (!m?.switchable) return null;

  async function pick(mode: "mock" | "claude") {
    if (mode === m!.mode) return;
    setBusy(true); setError(null);
    try { await setAIMode(mode); location.reload(); }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }
  const claudeTitle = m.claude_available ? "Use real Claude" : "Claude is not connected yet (needs the Claude engine and an API key)";
  return (
    <span className="ai-switch" role="group" aria-label="AI mode" title={signedIn ? undefined : "Sign in to switch"}>
      <span className="muted small">AI:</span>
      <button type="button" className={m.mode === "mock" ? "seg active" : "seg"} aria-pressed={m.mode === "mock"}
        disabled={busy || !signedIn} onClick={() => pick("mock")} title="Mocked answers, not real AI">AI-MK</button>
      <button type="button" className={m.mode === "claude" ? "seg active" : "seg"} aria-pressed={m.mode === "claude"}
        disabled={busy || !signedIn || !m.claude_available} onClick={() => pick("claude")} title={claudeTitle}>Claude</button>
      {!signedIn && <span className="muted small"> sign in to switch</span>}
      {error && <span role="alert" className="error small">{error}</span>}
    </span>
  );
}
