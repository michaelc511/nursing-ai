// White/red hospital theme by default; optional dark mode, remembered per browser.
export type Theme = "light" | "dark";
const KEY = "nurseopsnow.theme";

export function loadTheme(): Theme {
  try { return localStorage.getItem(KEY) === "dark" ? "dark" : "light"; } catch { return "light"; }
}

export function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem(KEY, t); } catch { /* storage blocked: theme lasts this visit */ }
}
