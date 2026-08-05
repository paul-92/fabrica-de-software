import type { Metadata } from "next";
import type { ReactNode } from "react";

import { loadBrandConfig } from "../branding/config";
import "../styles/globals.css";

const brand = loadBrandConfig();

export const metadata: Metadata = {
  title: brand.productName,
  description: "Configurable engineering operations platform.",
  icons: brand.faviconUrl ? { icon: brand.faviconUrl } : undefined,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
