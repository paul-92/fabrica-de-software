"use client";

import { useEffect, useState } from "react";

import { Button } from "./Button";

type Theme = "light" | "dark";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <Button
      variant="secondary"
      aria-label="Alternar tema"
      onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
    >
      Tema {theme === "light" ? "escuro" : "claro"}
    </Button>
  );
}
