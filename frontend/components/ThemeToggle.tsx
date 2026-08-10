"use client";

import { useSyncExternalStore } from "react";

import type { BrandTheme } from "../branding/types";
import { Button } from "./Button";

const STORAGE_KEY = "asep-theme";
const THEME_EVENT = "asep-theme-change";

type ThemeToggleProps = {
  defaultTheme: BrandTheme;
};

function isTheme(value: string | null): value is BrandTheme {
  return value === "light" || value === "dark";
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(THEME_EVENT, callback);

  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(THEME_EVENT, callback);
  };
}

export function ThemeToggle({ defaultTheme }: ThemeToggleProps) {
  const theme = useSyncExternalStore(
    subscribe,
    () => {
      const savedTheme = window.localStorage.getItem(STORAGE_KEY);
      return isTheme(savedTheme) ? savedTheme : defaultTheme;
    },
    () => defaultTheme,
  );

  function toggleTheme() {
    const nextTheme: BrandTheme = theme === "light" ? "dark" : "light";

    window.localStorage.setItem(STORAGE_KEY, nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    window.dispatchEvent(new Event(THEME_EVENT));
  }

  return (
    <Button
      variant="secondary"
      aria-label="Alternar tema"
      onClick={toggleTheme}
    >
      Tema {theme === "light" ? "escuro" : "claro"}
    </Button>
  );
}