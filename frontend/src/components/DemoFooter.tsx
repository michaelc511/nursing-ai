import { useEffect, useState } from "react";
import { aiMode, AIMode, setAIMode } from "../api";
import { useDebugMode } from "./DebugMode";

// Presenter-only: two words in the footer are invisible switches (demo mode only, inert in production).
// "Synthetic data only" flips AI-MK and Claude. "Medical Directors" flips debug mode.
export function DemoFooter() {
  const [m, setM] = useState<AIMode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debug = useDebugMode();
  useEffect(() => { aiMode().then(setM); }, []);

  async function toggleAI() {
    if (!m?.switchable || busy) return;
    const next = m.mode === "mock" ? "claude" : "mock";
    if (next === "claude" && !m.claude_available) { setError("Claude is not connected yet."); return; }
    setBusy(true); setError(null);
    try { await setAIMode(next); location.reload(); }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }

  return (
    <footer className="muted">
      <span className="hidden-toggle" onClick={toggleAI}>Synthetic data only</span>
      {" · AI never denies: decisions are made by Nurses and "}
      <span className="hidden-toggle" onClick={debug.toggle}>Medical Directors</span>
      {error && <span role="alert" className="error small"> {error}</span>}
    </footer>
  );
}
