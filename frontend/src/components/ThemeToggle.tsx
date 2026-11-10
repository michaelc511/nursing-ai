import { useEffect, useState } from "react";
import { applyTheme, loadTheme, Theme } from "../theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(loadTheme());
  useEffect(() => { applyTheme(theme); }, [theme]);
  return (
    <button type="button" className="theme-btn" onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}>
      {theme === "light" ? "Dark mode" : "Light mode"}
    </button>
  );
}
