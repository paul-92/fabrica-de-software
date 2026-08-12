import { describe, expect, it } from "vitest";

import {
  createBrandConfig,
  defaultBrandConfig,
  resolveBrandConfig,
} from "./config";

describe("brand configuration", () => {
  it("loads the neutral default brand", () => {
    expect(createBrandConfig()).toEqual(defaultBrandConfig);
    expect(defaultBrandConfig.productName).toBe("Engineering Platform");
  });

  it("overrides only institutional identity at runtime", () => {
    const buildTime = createBrandConfig({
      productName: "Build product",
      shortName: "BP",
      logoUrl: "https://build.example/logo.svg",
      faviconUrl: "/favicon.ico",
      primaryColor: "#112233",
      secondaryColor: "#445566",
      defaultTheme: "dark",
      workspaceLabel: "Build workspace",
      footerText: "Build footer",
    });
    const resolved = resolveBrandConfig(buildTime, {
      product_name: "Runtime product",
      short_name: "RT",
      logo_url: null,
      workspace_label: "Runtime workspace",
      footer_text: "Runtime footer",
    });

    expect(resolved).toEqual({
      ...buildTime,
      productName: "Runtime product",
      shortName: "RT",
      logoUrl: undefined,
      workspaceLabel: "Runtime workspace",
      footerText: "Runtime footer",
    });
    expect(resolved.faviconUrl).toBe("/favicon.ico");
    expect(resolved.primaryColor).toBe("#112233");
    expect(resolved.secondaryColor).toBe("#445566");
    expect(resolved.defaultTheme).toBe("dark");
    expect(Object.isFrozen(resolved)).toBe(true);
  });

  it("changes identity through configuration only", () => {
    const alternative = createBrandConfig({
      productName: "Acme Studio",
      shortName: "AS",
      primaryColor: "#112233",
    });

    expect(alternative.productName).toBe("Acme Studio");
    expect(alternative.shortName).toBe("AS");
    expect(alternative.primaryColor).toBe("#112233");
    expect(alternative.secondaryColor).toBe(defaultBrandConfig.secondaryColor);
  });
});
