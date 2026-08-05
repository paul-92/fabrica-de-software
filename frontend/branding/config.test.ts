import { describe, expect, it } from "vitest";

import { createBrandConfig, defaultBrandConfig } from "./config";

describe("brand configuration", () => {
  it("loads the neutral default brand", () => {
    expect(createBrandConfig()).toEqual(defaultBrandConfig);
    expect(defaultBrandConfig.productName).toBe("Engineering Platform");
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
