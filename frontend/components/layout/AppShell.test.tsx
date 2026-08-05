import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { createBrandConfig } from "../../branding/config";
import { AppHeader } from "./AppHeader";
import { navigationItems } from "./navigation";
import { Sidebar } from "./Sidebar";

const alternativeBrand = createBrandConfig({
  productName: "Northstar Studio",
  shortName: "NS",
  primaryColor: "#123456",
  secondaryColor: "#abcdef",
});

function renderSidebar(pathname = "/") {
  return renderToStaticMarkup(
    <Sidebar
      brand={alternativeBrand}
      pathname={pathname}
      mobileOpen={false}
      onNavigate={() => undefined}
    />,
  );
}

describe("application shell structure", () => {
  it("renders BrandMark from the supplied white-label configuration", () => {
    const markup = renderSidebar();

    expect(markup).toContain("Northstar Studio");
    expect(markup).toContain("NS");
  });

  it("offers every expected navigation destination", () => {
    const markup = renderSidebar();

    navigationItems.forEach(({ href, label }) => {
      expect(markup).toContain(`href="${href}"`);
      expect(markup).toContain(`>${label}</span>`);
    });
    expect(navigationItems).toHaveLength(8);
  });

  it("marks the current route accessibly", () => {
    const markup = renderSidebar("/knowledge");
    const activeLink = markup.match(/<a[^>]*href="\/knowledge"[^>]*>/)?.[0];

    expect(activeLink).toContain('class="nav-link nav-link--active"');
    expect(activeLink).toContain('aria-current="page"');
  });

  it("keeps ThemeToggle available in the global header", () => {
    const markup = renderToStaticMarkup(
      <AppHeader title="Knowledge" onOpenNavigation={() => undefined} />,
    );

    expect(markup).toContain("Alternar tema");
    expect(markup).toContain("Tema escuro");
  });

  it("does not bind shell components to a fixed product identity", () => {
    const files = ["AppShell.tsx", "Sidebar.tsx", "AppHeader.tsx"];
    const source = files
      .map((file) =>
        readFileSync(
          fileURLToPath(new URL(`./${file}`, import.meta.url)),
          "utf8",
        ),
      )
      .join("\n");

    expect(source).not.toContain("ASEP");
    expect(source).not.toContain("Engineering Platform");
  });
});
