// Daily unit board shown after the intro (like a UM team's huddle notes). Demo content (synthetic), dated from today.
const fmt = (d: Date) => d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });

export function Notices({ today = new Date() }: { today?: Date }) {
  const items: { when: string; tag: string; text: string }[] = [
    { when: `${fmt(today)} · 7:00 AM`, tag: "Shift change",
      text: "Day shift: Nora Diaz, RN (lead) and Sam Patel, RN. Medical Director on call: Dr. Alex Kim, peer-to-peer calls 2–4 PM. Intake: Riley Chen." },
    { when: fmt(today), tag: "Policy",
      text: "MRI lumbar spine (72148): needs 6+ weeks of PT or medication first, unless there is a red flag (cancer history, infection, fracture, cauda equina, worsening weakness). Say which applies in your rationale." },
  ];
  return (
    <section className="notices card" aria-label="Unit board">
      <h3>Unit board · {fmt(today)}</h3>
      <ul>{items.map((n) => (
        <li key={n.tag + n.when}><span className={`ntag ntag-${n.tag.replace(/\s/g, "").toLowerCase()}`}>{n.tag}</span>
          <span className="nwhen">{n.when}</span><br />{n.text}</li>))}</ul>
    </section>
  );
}
