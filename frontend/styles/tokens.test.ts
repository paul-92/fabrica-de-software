import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const tokens = readFileSync(
  fileURLToPath(new URL("./tokens.css", import.meta.url)),
  "utf8",
);
const components = readFileSync(
  fileURLToPath(new URL("./globals.css", import.meta.url)),
  "utf8",
);

const requiredTokens = [
  "--color-background",
  "--color-surface",
  "--color-surface-elevated",
  "--color-text-primary",
  "--color-text-secondary",
  "--color-border",
  "--color-brand-primary",
  "--color-brand-secondary",
  "--color-success",
  "--color-warning",
  "--color-danger",
];

describe("design tokens", () => {
  it("defines every semantic token for the light theme", () => {
    const light = tokens.slice(0, tokens.indexOf('[data-theme="dark"]'));
    requiredTokens.forEach((token) => expect(light).toContain(token));
  });

  it("defines every semantic token for the dark theme", () => {
    const dark = tokens.slice(tokens.indexOf('[data-theme="dark"]'));
    requiredTokens.forEach((token) => expect(dark).toContain(token));
  });

  it("styles components through semantic tokens", () => {
    expect(components).toContain("var(--color-brand-primary)");
    expect(components).toContain("var(--color-surface)");
    expect(components).toContain("var(--color-text-primary)");
    expect(components).not.toMatch(/\.button[^}]+#[0-9a-f]{3,8}/i);
  });
});
