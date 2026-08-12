// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createBrandConfig } from "../../branding/config";
import type { RuntimeBrandingDto } from "../../lib/api/dtos";
import type { BrandingLoader } from "../../lib/services/branding";
import { AppShell } from "./AppShell";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

afterEach(cleanup);

const fallback = createBrandConfig({
  productName: "Build Product",
  shortName: "BP",
  logoUrl: undefined,
  faviconUrl: "/build-favicon.ico",
  primaryColor: "#112233",
  secondaryColor: "#445566",
  defaultTheme: "dark",
  workspaceLabel: "Build Workspace",
  footerText: "Build Footer",
});

const runtime = (overrides: Partial<RuntimeBrandingDto> = {}): RuntimeBrandingDto => ({
  product_name: "Runtime Product",
  short_name: "RP",
  logo_url: "https://cdn.example.com/runtime.svg",
  workspace_label: "Runtime Workspace",
  footer_text: "Runtime Footer",
  ...overrides,
});

const loader = (getBranding: BrandingLoader["getBranding"]): BrandingLoader => ({
  getBranding,
});

describe("AppShell runtime branding boundary", () => {
  it("renders build-time branding immediately and throughout loading", () => {
    const getBranding = vi.fn(() => new Promise<RuntimeBrandingDto>(() => undefined));
    const view = render(
      <AppShell brand={fallback} brandingLoader={loader(getBranding)}>
        <p>Page</p>
      </AppShell>,
    );

    expect(screen.getByText("Build Product")).toBeTruthy();
    expect(screen.getByText("BP")).toBeTruthy();
    expect(screen.getByText("Build Workspace")).toBeTruthy();
    expect(screen.getByText("Build Footer")).toBeTruthy();
    expect(view.container.firstElementChild?.getAttribute("style")).toContain("#112233");
    expect(getBranding).toHaveBeenCalledOnce();
  });

  it("updates every institutional consumer from one successful request", async () => {
    const getBranding = vi.fn().mockResolvedValue(runtime());
    const view = render(
      <AppShell brand={fallback} brandingLoader={loader(getBranding)}>
        <p>Page</p>
      </AppShell>,
    );

    expect(await screen.findByText("Runtime Product")).toBeTruthy();
    expect(screen.getByText("Runtime Workspace")).toBeTruthy();
    expect(screen.getByText("Runtime Footer")).toBeTruthy();
    const image = view.container.querySelector("img.brand-mark__image");
    expect(image?.getAttribute("src")).toBe("https://cdn.example.com/runtime.svg");
    expect(image?.parentElement?.textContent).toContain("RP");
    expect(getBranding).toHaveBeenCalledOnce();

    const style = view.container.firstElementChild?.getAttribute("style") ?? "";
    expect(style).toContain("#112233");
    expect(style).toContain("#445566");
    expect(screen.getByRole("button", { name: "Alternar tema" }).textContent).toContain("claro");
  });

  it("uses the runtime short name when logo is null", async () => {
    render(
      <AppShell brand={fallback} brandingLoader={loader(
        vi.fn().mockResolvedValue(runtime({ logo_url: null })),
      )}>
        <p>Page</p>
      </AppShell>,
    );
    expect(await screen.findByText("RP")).toBeTruthy();
    expect(document.querySelector("img.brand-mark__image")).toBeNull();
  });

  it("keeps textual identity and reveals short name if an image fails", async () => {
    const view = render(
      <AppShell brand={fallback} brandingLoader={loader(
        vi.fn().mockResolvedValue(runtime()),
      )}>
        <p>Page</p>
      </AppShell>,
    );
    await screen.findByText("Runtime Product");
    const image = view.container.querySelector("img.brand-mark__image") as HTMLImageElement;
    const glyph = image.nextElementSibling as HTMLElement;
    expect(glyph.hidden).toBe(true);
    fireEvent.error(image);
    expect(image.hidden).toBe(true);
    expect(glyph.hidden).toBe(false);
    expect(glyph.textContent).toBe("RP");
    expect(screen.getByLabelText("Runtime Product")).toBeTruthy();
  });

  it("keeps fallback on error and retries without hiding the shell", async () => {
    const getBranding = vi.fn()
      .mockRejectedValueOnce(new Error("private backend detail"))
      .mockResolvedValueOnce(runtime());
    render(
      <AppShell brand={fallback} brandingLoader={loader(getBranding)}>
        <p>Page</p>
      </AppShell>,
    );

    expect(await screen.findByText("A identidade atual foi preservada.")).toBeTruthy();
    expect(screen.getByText("Build Product")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(screen.getByText("Build Product")).toBeTruthy();
    expect(await screen.findByText("Runtime Product")).toBeTruthy();
    expect(getBranding).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(/private backend detail/i)).toBeNull();
  });

  it("ignores an older response when a retry finishes first", async () => {
    let resolveFirst!: (value: RuntimeBrandingDto) => void;
    let resolveSecond!: (value: RuntimeBrandingDto) => void;
    const first = new Promise<RuntimeBrandingDto>((resolve) => {
      resolveFirst = resolve;
    });
    const second = new Promise<RuntimeBrandingDto>((resolve) => {
      resolveSecond = resolve;
    });
    const firstLoader = loader(vi.fn().mockReturnValue(first));
    const secondLoader = loader(vi.fn().mockReturnValue(second));
    const view = render(
      <AppShell brand={fallback} brandingLoader={firstLoader}>
        <p>Page</p>
      </AppShell>,
    );

    view.rerender(
      <AppShell brand={fallback} brandingLoader={secondLoader}>
        <p>Page</p>
      </AppShell>,
    );
    await act(async () => {
      resolveSecond(runtime({ product_name: "Newest Product" }));
    });
    expect(await screen.findByText("Newest Product")).toBeTruthy();
    await act(async () => { resolveFirst(runtime({ product_name: "Stale Product" })); });
    expect(screen.queryByText("Stale Product")).toBeNull();
    expect(screen.getByText("Newest Product")).toBeTruthy();
  });

  it("handles maximum-length identity without changing shell ownership", async () => {
    const long = runtime({
      product_name: "P".repeat(120),
      short_name: "S".repeat(12),
      workspace_label: "W".repeat(80),
      footer_text: "F".repeat(200),
      logo_url: null,
    });
    render(
      <AppShell brand={fallback} brandingLoader={loader(vi.fn().mockResolvedValue(long))}>
        <p>Page</p>
      </AppShell>,
    );
    expect(await screen.findByText(long.product_name)).toBeTruthy();
    expect(screen.getByText(long.short_name)).toBeTruthy();
    expect(screen.getByText(long.workspace_label)).toBeTruthy();
    expect(screen.getByText(long.footer_text)).toBeTruthy();
  });
});
