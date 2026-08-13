import type { Metadata } from "next";
import type { ReactNode } from "react";

import { loadBrandConfig } from "../branding/config";
import { AppShell } from "../components/layout/AppShell";
import { AccessGate } from "../components/access/AccessGate";
import "../styles/globals.css";

const brand = loadBrandConfig();

export const metadata: Metadata = {
  title: brand.productName,
  description: "Plataforma de operações de engenharia de software.",
  icons: brand.faviconUrl ? { icon: brand.faviconUrl } : undefined,
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      data-theme={brand.defaultTheme}
      suppressHydrationWarning
    >
      <body>
        <AccessGate><AppShell brand={brand}>{children}</AppShell></AccessGate>
      </body>
    </html>
  );
}
