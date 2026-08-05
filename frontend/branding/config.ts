import type { BrandConfig } from "./types";

export const defaultBrandConfig: BrandConfig = Object.freeze({
  productName: "Engineering Platform",
  shortName: "EP",
  primaryColor: "#6750e8",
  secondaryColor: "#20b8a6",
});

export function createBrandConfig(
  overrides: Partial<BrandConfig> = {},
): BrandConfig {
  return Object.freeze({ ...defaultBrandConfig, ...overrides });
}

export function loadBrandConfig(): BrandConfig {
  return createBrandConfig({
    productName:
      process.env.NEXT_PUBLIC_PRODUCT_NAME ?? defaultBrandConfig.productName,
    shortName:
      process.env.NEXT_PUBLIC_SHORT_NAME ?? defaultBrandConfig.shortName,
    logoUrl: process.env.NEXT_PUBLIC_LOGO_URL || undefined,
    faviconUrl: process.env.NEXT_PUBLIC_FAVICON_URL || undefined,
    primaryColor:
      process.env.NEXT_PUBLIC_PRIMARY_COLOR ?? defaultBrandConfig.primaryColor,
    secondaryColor:
      process.env.NEXT_PUBLIC_SECONDARY_COLOR ??
      defaultBrandConfig.secondaryColor,
  });
}
