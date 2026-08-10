// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
} from "vitest";

import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    cleanup();
  });

  it("uses the configured default theme when no preference is stored", () => {
    render(<ThemeToggle defaultTheme="dark" />);

    const button = screen.getByRole("button", {
      name: "Alternar tema",
    });

    expect(button.textContent).toContain("Tema claro");
  });

  it("restores the theme previously stored by the user", () => {
    window.localStorage.setItem("asep-theme", "light");

    render(<ThemeToggle defaultTheme="dark" />);

    const button = screen.getByRole("button", {
      name: "Alternar tema",
    });

    expect(button.textContent).toContain("Tema escuro");
  });

  it("persists the new theme and applies it to the document", () => {
    render(<ThemeToggle defaultTheme="light" />);

    const button = screen.getByRole("button", {
      name: "Alternar tema",
    });

    fireEvent.click(button);

    expect(window.localStorage.getItem("asep-theme")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(button.textContent).toContain("Tema claro");
  });
});