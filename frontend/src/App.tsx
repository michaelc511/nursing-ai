import { useState } from "react";
import { getSession, logout, User } from "./api";
import { HelpButton } from "./components/Help";
import { Intro } from "./components/Intro";
import { Notices } from "./components/Notices";
import { PolicyRow } from "./components/PolicyRow";
import { LastRun } from "./components/LastRun";
import { ThemeToggle } from "./components/ThemeToggle";
import { HelpChat, startTour } from "./components/HelpChat";
import { HiddenReset } from "./components/HiddenReset";
import { roleName } from "./roles";
import { MockBanner } from "./components/MK";
import { MetricsHeader } from "./components/MetricsHeader";
import { CaseDetail } from "./pages/CaseDetail";
import { Login } from "./pages/Login";
import { Queue } from "./pages/Queue";

export default function App() {
  const [user, setUser] = useState<User | null>(getSession()?.user ?? null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((k) => k + 1);

  if (!user) return <><MockBanner /><Login onLogin={setUser} /><HelpChat screen="login" /></>;
  return (
    <>
      <header className="top">
        <div className="brand"><img src="/nurse.svg" alt="" width={40} height={40} /> NurseOps Now<HiddenReset /></div>
        <div className="who"><button type="button" className="theme-btn" onClick={startTour}>AI Assist</button> <ThemeToggle /> <HelpButton screen={openId === null ? "queue" : "case"} role={user.role} /> {user.full_name} · {roleName(user.role)}
          <button className="link" data-tour="signout" onClick={() => { logout(); setUser(null); setOpenId(null); }}>Sign out</button></div>
      </header>
      <MockBanner />
      <div data-tour="metrics"><MetricsHeader refreshKey={refreshKey} /></div>
      <main className="content">
        {openId === null && <><Intro role={user.role} /><Notices /><LastRun refreshKey={refreshKey} /></>}
        {openId === null
          ? <><Queue onOpen={setOpenId} onChange={refresh} refreshKey={refreshKey} /><PolicyRow /></>
          : <CaseDetail id={openId} onBack={() => { setOpenId(null); refresh(); }} onChange={refresh} />}
      </main>
      <HelpChat screen={openId === null ? "queue" : "case"} role={user.role} openId={openId} refreshKey={refreshKey} />
      <footer className="muted">Synthetic data only · AI never denies: decisions are made by Nurses and Medical Directors</footer>
    </>
  );
}
