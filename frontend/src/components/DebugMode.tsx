import { useEffect, useState } from "react";
import { AIMode } from "../api";
import { useAIMode } from "./MK";

// Debug details on case pages. Demo mode: presenter toggle, remembered for the browser tab.
// Production (DEMO_MODE off): only the server's DEBUG_UI setting counts.
const KEY = "nurseopsnow.debug";
const CHANGED = "nurseopsnow:debug-changed";

function isOn(mode: AIMode | null): boolean {
  if (!mode) return false;
  if (mode.demo) {
    try {
      const saved = sessionStorage.getItem(KEY);
      if (saved !== null) return saved === "1";
    } catch { /* storage blocked: use the server default */ }
  }
  return !!mode.debug;
}

export function useDebugMode() {
  const mode = useAIMode();
  const [, redraw] = useState(0);
  useEffect(() => {
    const update = () => redraw((n) => n + 1);
    window.addEventListener(CHANGED, update);
    return () => window.removeEventListener(CHANGED, update);
  }, []);
  const on = isOn(mode);
  function toggle() {
    if (!mode?.demo) return;
    try { sessionStorage.setItem(KEY, on ? "0" : "1"); } catch { return; }
    window.dispatchEvent(new Event(CHANGED));
  }
  return { on, toggle };
}

export function DebugBanner() {
  const { on } = useDebugMode();
  if (!on) return null;
  return <div className="mk-banner" role="note"><b>Debug mode on.</b> Case pages show AI tokens, cost, traces and search scores.</div>;
}
