import { describe, expect, it } from "vitest";

import { ApiConfigurationError, createApiConfig, loadApiConfig } from "./config";

describe("API configuration", () => {
  it("loads the base URL exclusively from NEXT_PUBLIC_API_URL", () => {
    expect(
      loadApiConfig("https://platform.example/"),
    ).toEqual({ baseUrl: "https://platform.example" });
  });

  it("normalizes surrounding spaces and removes the trailing slash", () => {
    expect(createApiConfig("  https://platform.example/api/v1/  ")).toEqual({
      baseUrl: "https://platform.example/api/v1",
    });
  });

  it("returns the canonical URL produced by the parser", () => {
    expect(createApiConfig("HTTPS://PLATFORM.EXAMPLE:443/api/v1/")).toEqual({
      baseUrl: "https://platform.example/api/v1",
    });
  });

  it("preserves a valid normalized URL without a trailing slash", () => {
    const config = createApiConfig("http://localhost:8000/api/v1");

    expect(config.baseUrl).toBe("http://localhost:8000/api/v1");
    expect(Object.isFrozen(config)).toBe(true);
  });

  it.each([undefined, "", "relative/api", "file:///tmp/api"])(
    "rejects invalid public API URL %s",
    (value) => {
      expect(() => createApiConfig(value)).toThrow(ApiConfigurationError);
    },
  );
});
