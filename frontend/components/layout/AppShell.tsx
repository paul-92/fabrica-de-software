"use client";

import { usePathname } from "next/navigation";
import type { PropsWithChildren } from "react";
import { useState } from "react";

import type { BrandConfig } from "../../branding/types";
import { AppHeader } from "./AppHeader";
import { titleForPath } from "./navigation";
import { Sidebar } from "./Sidebar";

type AppShellProps = PropsWithChildren<{ brand: BrandConfig }>;

export function AppShell({ brand, children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        brand={brand}
        pathname={pathname}
        mobileOpen={mobileOpen}
        onNavigate={() => setMobileOpen(false)}
      />
      {mobileOpen ? (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Fechar navegação"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}
      <div className="app-shell__workspace">
        <AppHeader
          title={titleForPath(pathname)}
          onOpenNavigation={() => setMobileOpen(true)}
        />
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
