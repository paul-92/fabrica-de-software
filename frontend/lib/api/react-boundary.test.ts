import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { globSync } from "node:fs";

describe("React HTTP boundary", () => {
  it("keeps fetch out of every React component", () => {
    const frontendRoot = fileURLToPath(new URL("../../", import.meta.url));
    const files = globSync("{app,components}/**/*.tsx", { cwd: frontendRoot });

    expect(files.length).toBeGreaterThan(0);
    files.forEach((file) => {
      const source = readFileSync(`${frontendRoot}/${file}`, "utf8");
      expect(source).not.toMatch(/\bfetch\s*\(/);
    });
  });
});
