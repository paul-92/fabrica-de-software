import type { Metadata } from "next";
import type { ReactNode } from "react";

import { loadBrandConfig } from "../branding/config";
import { AppShell } from "../components/layout/AppShell";
import "../styles/globals.css";

const brand = loadBrandConfig();

export const metadata: Metadata = {
  title: brand.productName,
  description: "Plataforma de operações de engenharia de software.",
  icons: brand.faviconUrl ? { icon: brand.faviconUrl } : undefined,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <AppShell brand={brand}>{children}</AppShell>
      </body>
    </html>
  );
}
