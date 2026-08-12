import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import { ApiClient } from "../api/client";
import { ApiResponseError } from "../api/errors";
import {
  BrandingClient,
  BrandingService,
  createBrandingLoader,
  parseRuntimeBranding,
} from "./branding";

const payload = (logo_url: string | null = null) => ({
  product_name: "Runtime Product",
  short_name: "RP",
  logo_url,
  workspace_label: "Runtime workspace",
  footer_text: "Runtime footer",
});

describe("runtime branding service", () => {
  it("requests the public endpoint and parses exactly five fields", async () => {
    const request = vi.fn().mockResolvedValue(payload(null));
    const client = new BrandingClient({ request } as unknown as ApiClient);
    const result = await client.get();

    expect(request).toHaveBeenCalledWith({ path: "/api/v1/branding" });
    expect(result).toEqual(payload(null));
    expect(Object.keys(result)).toEqual([
      "product_name", "short_name", "logo_url", "workspace_label", "footer_text",
    ]);
    expect(Object.isFrozen(result)).toBe(true);
  });

  it("accepts an HTTPS logo and null logo", () => {
    expect(parseRuntimeBranding(payload(null)).logo_url).toBeNull();
    expect(
      parseRuntimeBranding(payload("https://cdn.example.com/logo.svg")).logo_url,
    ).toBe("https://cdn.example.com/logo.svg");
  });

  it.each([
    null,
    {},
    { ...payload(), product_name: 1 },
    { ...payload(), logo_url: false },
    { ...payload(), metadata: {} },
  ])("rejects an invalid public contract", (invalid) => {
    expect(() => parseRuntimeBranding(invalid)).toThrow(ApiResponseError);
  });

  it("propagates HTTP failures", async () => {
    const failure = new Error("unavailable");
    const client = new BrandingClient({
      request: vi.fn().mockRejectedValue(failure),
    } as unknown as ApiClient);
    await expect(client.get()).rejects.toBe(failure);
  });

  it("creates clients lazily once while allowing repeated loads", async () => {
    const get = vi.fn().mockResolvedValue(payload());
    const factory = vi.fn().mockReturnValue({ branding: { get } });
    const loader = createBrandingLoader(factory);

    expect(factory).not.toHaveBeenCalled();
    await loader.getBranding();
    await loader.getBranding();
    expect(factory).toHaveBeenCalledOnce();
    expect(get).toHaveBeenCalledTimes(2);

    const apiRequest = vi.fn().mockResolvedValue(payload());
    await expect(
      new BrandingService({
        branding: new BrandingClient(
          { request: apiRequest } as unknown as ApiClient,
        ),
      }).getBranding(),
    ).resolves.toEqual(payload());
  });

  it("keeps React behind the service boundary without frontend persistence", () => {
    const shell = readFileSync(
      new URL("../../components/layout/AppShell.tsx", import.meta.url),
      "utf8",
    );
    const service = readFileSync(new URL("./branding.ts", import.meta.url), "utf8");

    expect(shell).not.toMatch(/\bfetch\s*\(/);
    expect(shell).not.toContain("localStorage");
    expect(shell).not.toMatch(/asep\.(branding|repositories|api)/i);
    expect(service).toContain('path: "/api/v1/branding"');
    expect(service).not.toContain("localStorage");
    expect(service).not.toMatch(/\.py["']/);
  });
});
