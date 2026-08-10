export type BrandTheme = "light" | "dark";

export type BrandConfig = Readonly<{
  productName: string;
  shortName: string;
  logoUrl?: string;
  faviconUrl?: string;
  primaryColor: string;
  secondaryColor: string;
  defaultTheme: BrandTheme;
  workspaceLabel: string;
  footerText: string;
}>;