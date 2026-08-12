"use client";

import { usePathname } from "next/navigation";
import type { CSSProperties, PropsWithChildren } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { resolveBrandConfig } from "../../branding/config";
import type { BrandConfig } from "../../branding/types";
import { createPlatformClients } from "../../lib/api";
import type { RuntimeBrandingDto } from "../../lib/api/dtos";
import {
  createBrandingLoader,
  type BrandingLoader,
} from "../../lib/services/branding";
import { AppHeader } from "./AppHeader";
import { titleForPath } from "./navigation";
import { Sidebar } from "./Sidebar";

type AppShellProps = PropsWithChildren<{
  brand: BrandConfig;
  brandingLoader?: BrandingLoader;
}>;

export function AppShell({ brand, brandingLoader, children }: AppShellProps) {
  const pathname = usePathname();
  const loader = useMemo(
    () => brandingLoader ?? createBrandingLoader(createPlatformClients),
    [brandingLoader],
  );
  const requestVersion = useRef(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [runtimeBrand, setRuntimeBrand] = useState<RuntimeBrandingDto | null>(null);
  const [brandingError, setBrandingError] = useState(false);
  const [brandingAttempt, setBrandingAttempt] = useState(0);
  const resolvedBrand = runtimeBrand
    ? resolveBrandConfig(brand, runtimeBrand)
    : brand;

  useEffect(() => {
    const version = ++requestVersion.current;
    loader.getBranding().then(
      (loaded) => {
        if (version !== requestVersion.current) return;
        setRuntimeBrand(loaded);
        setBrandingError(false);
      },
      () => {
        if (version !== requestVersion.current) return;
        setBrandingError(true);
      },
    );
  }, [loader, brandingAttempt]);

  function retryBranding() {
    requestVersion.current += 1;
    setBrandingError(false);
    setBrandingAttempt((value) => value + 1);
  }

  const brandStyles = {
    "--brand-primary": resolvedBrand.primaryColor,
    "--brand-secondary": resolvedBrand.secondaryColor,
  } as CSSProperties;

  return (
    <div className="app-shell" style={brandStyles}>
      <Sidebar
        brand={resolvedBrand}
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
          brand={resolvedBrand}
          onOpenNavigation={() => setMobileOpen(true)}
        />

        {brandingError ? (
          <div className="branding-notice" role="status">
            <span>A identidade atual foi preservada.</span>
            <button type="button" onClick={retryBranding}>
              Tentar novamente
            </button>
          </div>
        ) : null}

        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
