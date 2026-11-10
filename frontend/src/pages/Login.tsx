import { FormEvent, useEffect, useState } from "react";
import { demoPassword, login, User } from "../api";
import { HelpButton } from "../components/Help";
import { Intro } from "../components/Intro";
import { ThemeToggle } from "../components/ThemeToggle";
import { startTour } from "../components/HelpChat";
import { AISwitch } from "../components/AISwitch";

export function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [username, setUsername] = useState("nurse1");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { demoPassword().then((p) => { if (p) setPassword(p); }); }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { onLogin(await login(username, password)); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <main className="login">
      <div className="login-top"><button type="button" className="theme-btn" onClick={startTour}>AI Assist</button> <AISwitch signedIn={false} /> <ThemeToggle /></div>
      <form onSubmit={submit} className="card" data-tour="login">
        <div className="toolbar"><img src="/nurse.svg" alt="" width={44} height={44} /><h1>NurseOps Now</h1><HelpButton screen="login" /></div>
        <p className="muted">AI-assisted prior authorization · synthetic demo data</p>
        <Intro />
        <label>User
          <select value={username} onChange={(e) => setUsername(e.target.value)}>
            <option value="nurse1">nurse1 (Nurse)</option>
            <option value="nurse2">nurse2 (Nurse)</option>
            <option value="meddir">meddir (Medical Director)</option>
            <option value="intake1">intake1 (Intake Coordinator)</option>
          </select>
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
