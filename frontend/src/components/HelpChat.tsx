import { FormEvent, useEffect, useRef, useState } from "react";
import { assistChat, assistClear, CaseSummary, listCases, Source } from "../api";
import { Feedback } from "./Feedback";
import { nextStep } from "../guide";
import { ABOUT, Screen, STEPS, WORKFLOW } from "./Help";
import { roleName } from "../roles";
import { MK, useAIMode } from "./MK";

// AI Assist, bottom-right: the one place for all AI help.
// Typed questions (signed in) go to the backend agent: Claude with read-only tools + policy/guide RAG
// (AI-MK rule router without a key). Chips and "Guide me" stay scripted and instant (the fallback too).
type Msg = { from: "bot" | "me"; text: string; who?: string; sources?: Source[]; engine?: string;
             q?: string; debug?: string; pending?: boolean };
type State = { open: boolean; msgs: Msg[]; guiding: boolean; target?: string };

const KEY = "nurseopsnow.helpchat";
const EVENT = "nurseopsnow-helpchat";
const HELLO: Msg = { from: "bot", text: "Hi! I'm AI Assist. Ask me about a case, a policy or this app, or tap Guide me for the next step. Answers say where they come from (AI = Claude, AI-MK = prepared answers)." };

function load(): State {
  try { const v = sessionStorage.getItem(KEY); if (v) return JSON.parse(v); } catch { /* ignore */ }
  return { open: false, msgs: [HELLO], guiding: false };
}
function save(s: State) { try { sessionStorage.setItem(KEY, JSON.stringify(s)); } catch { /* ignore */ } }

const RULES = [
  "AI never decides: only a Nurse or Medical Director approves, denies or pends.",
  "Only the Medical Director can deny. A Nurse who thinks a request doesn't meet the policy pends it for MD review.",
  "Every decision needs a short reason.",
  "If something is missing, the provider is asked for it, and the case comes back when it arrives.",
  "Everything anyone does is recorded in the audit log.",
];

export function startTour() { window.dispatchEvent(new Event(EVENT)); }

function answer(q: string, screen: Screen, role?: string): Msg[] {
  const t = q.toLowerCase();
  const bot = (text: string): Msg => ({ from: "bot", text });
  if (/role|my job|can i|who/.test(t)) {
    if (!role) return [bot("You're not signed in yet. Each person has a job:"), ...WORKFLOW.filter((w) => w.role).map((w) => bot(`${w.who}: ${w.does}`))];
    return [bot(`You are the ${roleName(role)}.`), ...WORKFLOW.filter((w) => w.role === role).map((w) => bot(w.does))];
  }
  if (/screen|here|page/.test(t)) return [bot(`On this screen (${STEPS[screen].title}):`), ...STEPS[screen].steps.map(bot)];
  if (/rule|reason/.test(t)) return RULES.map(bot);
  if (/about|what is|why|goal/.test(t)) return ABOUT.map(bot);
  if (/password|login|sign/.test(t)) return [bot("Pick a user, enter the demo password (local demos fill it in) and click Sign in. Users: intake1 (Intake Coordinator), nurse1 and nurse2 (Nurse), meddir (Medical Director).")];
  if (/case|why|missing|deny|approve|tier|quote/.test(t)) return [bot("Questions about a specific case will be answered by Claude here, with quotes from the request and the policy (coming next phase). For now, open the case and read its AI review (AI-MK).")];
  return [bot("I can guide you through the app. Tap Guide me, or ask about your role, this screen or the rules.")];
}

export function HelpChat({ screen, role, openId = null, refreshKey = 0 }:
  { screen: Screen; role?: string; openId?: number | null; refreshKey?: number }) {
  const [st, setSt] = useState<State>(load());
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const mode = useAIMode();
  const update = (fn: (s: State) => State) => setSt((s) => { const n = fn(s); save(n); return n; });

  useEffect(() => {
    const on = () => update((s) => ({ ...s, open: true, guiding: true, msgs: [...s.msgs, { from: "me", text: "Guide me" }] }));
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);

  // Live data for the guide (only while guiding and signed in).
  useEffect(() => {
    if (!st.guiding || !role) { setCases(null); return; }
    let live = true;
    listCases().then((c) => live && setCases(c)).catch(() => live && setCases([]));
    return () => { live = false; };
  }, [st.guiding, role, refreshKey, openId]);

  // Post the next step whenever it changes.
  useEffect(() => {
    if (!st.guiding || (role && !cases)) return;
    const g = nextStep(role, cases, openId);
    update((s) => {
      const last = [...s.msgs].reverse().find((m) => m.from === "bot");
      if (last?.text === g.text) return { ...s, target: g.target };
      return { ...s, target: g.target, msgs: [...s.msgs, { from: "bot", who: g.who, text: g.text }] };
    });
  }, [st.guiding, role, cases, openId, screen]);

  useEffect(() => { endRef.current?.scrollIntoView?.({ block: "end" }); }, [st.msgs.length, st.open]);

  // Outline the thing to click.
  useEffect(() => {
    const target = st.guiding ? st.target : undefined;
    const mark = () => {
      document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target"));
      if (target) document.querySelector(`[data-tour="${target}"]`)?.classList.add("tour-target");
    };
    mark();
    const timer = window.setInterval(mark, 700);
    return () => { window.clearInterval(timer); document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target")); };
  }, [st.guiding, st.target]);

  const scripted = (q: string) => {
    if (/guide|walk|tour|next step|start/i.test(q)) return update((s) => ({ ...s, guiding: true, msgs: [...s.msgs, { from: "me", text: q }] }));
    update((s) => ({ ...s, msgs: [...s.msgs, { from: "me", text: q }, ...answer(q, screen, role)] }));
  };
  const ask = async (q: string) => {
    if (!role || /^(guide me|walk me|start)$/i.test(q)) return scripted(q);
    update((s) => ({ ...s, msgs: [...s.msgs, { from: "me", text: q }, { from: "bot", text: "Thinking…", pending: true }] }));
    let reply: Msg[];
    try {
      const r = await assistChat(q, openId);
      const debug = mode?.debug ? `tools: ${r.tools_used.join(", ") || "none"}${r.rewritten ? ` · rewritten: ${r.rewritten}` : ""}${r.blocked ? ` · blocked: ${r.blocked}` : ""}` : undefined;
      reply = [{ from: "bot", text: r.answer, sources: r.sources, engine: r.engine, q, debug }];
    } catch (e) {
      reply = [{ from: "bot", text: `AI Assist couldn't answer (${(e as Error).message}). Here's the built-in guide instead:` },
               ...answer(q, screen, role)];
    }
    update((s) => ({ ...s, msgs: [...s.msgs.filter((m) => !m.pending), ...reply] }));
  };
  const stop = () => update((s) => ({ ...s, guiding: false, target: undefined,
    msgs: [...s.msgs, { from: "me", text: "Stop guiding" }, { from: "bot", text: "OK, guide stopped. Tap Guide me any time." }] }));
  const submit = (e: FormEvent) => { e.preventDefault(); if (input.trim()) { ask(input.trim()); setInput(""); } };

  if (!st.open) return <button type="button" className="chat-launcher" onClick={() => update((s) => ({ ...s, open: true }))}>AI Assist <MK /></button>;
  return (
    <aside className="chat card" aria-label="Help chat">
      <div className="chat-head">
        <b>AI Assist <MK />{st.guiding && <span className="muted"> · guiding</span>}</b>
        <span>
          <button type="button" className="link" onClick={() => {
            if (role) assistClear(openId).catch(() => undefined);   // clears the saved chat memory too
            update(() => ({ open: true, msgs: [HELLO], guiding: false }));
          }}>Clear</button>
          <button type="button" className="link" aria-label="Close help chat" onClick={() => update((s) => ({ ...s, open: false }))}>×</button>
        </span>
      </div>
      <div className="chat-body">
        {st.msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.from}${m.pending ? " pending" : ""}`} aria-busy={m.pending || undefined}>
            {m.from === "bot" && <div className="bubble-mk">{m.engine === "AI" ? <span className="muted small">AI</span>
              : m.engine === "guard" ? <span className="muted small">safety check</span> : <MK busy={m.pending} />}</div>}
            {m.who && <div className="bubble-who">{m.who}</div>}
            <span className="bubble-text">{m.text}</span>
            {m.sources && m.sources.length > 0 && (
              <ul className="sources small">{m.sources.map((s, j) => <li key={j}>{s.label}</li>)}</ul>)}
            {m.debug && <div className="muted small debug-line">{m.debug}</div>}
            {m.q && m.engine !== "guard" && <Feedback kind="assist" caseId={openId} question={m.q} />}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="chips">
        {st.guiding
          ? <button type="button" className="chip" onClick={stop}>Stop guiding</button>
          : <button type="button" className="chip primary" onClick={() => scripted("Guide me")}>Guide me</button>}
        <button type="button" className="chip" onClick={() => scripted("What does my role do?")}>My role</button>
        <button type="button" className="chip" onClick={() => scripted("What do I do on this screen?")}>This screen</button>
        <button type="button" className="chip" onClick={() => scripted("What are the rules?")}>Rules</button>
        <button type="button" className="chip" onClick={() => scripted("What is NurseOps Now?")}>About</button>
      </div>
      <form className="chat-input" onSubmit={submit}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={role ? (openId ? `Ask about case ${openId}, a policy or the app…` : "Ask about a case, a policy or the app…") : "Ask about this app…"} aria-label="Ask a help question" />
        <button>Send</button>
      </form>
    </aside>
  );
}
