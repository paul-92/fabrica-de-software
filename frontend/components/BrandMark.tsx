import type { CSSProperties } from "react";

import type { BrandConfig } from "../branding/types";

type BrandMarkProps = {
  brand: BrandConfig;
};

type BrandTokens = CSSProperties & {
  "--brand-primary": string;
  "--brand-secondary": string;
};

export function BrandMark({ brand }: BrandMarkProps) {
  const tokens: BrandTokens = {
    "--brand-primary": brand.primaryColor,
    "--brand-secondary": brand.secondaryColor,
  };

  return (
    <div className="brand-mark" style={tokens} aria-label={brand.productName}>
      {brand.logoUrl ? (
        // A configurable remote logo deliberately uses a plain image element.
        // eslint-disable-next-line @next/next/no-img-element
        <img className="brand-mark__image" src={brand.logoUrl} alt="" />
      ) : (
        <span className="brand-mark__glyph" aria-hidden="true">
          {brand.shortName}
        </span>
      )}
      <span className="brand-mark__name">{brand.productName}</span>
    </div>
  );
}
