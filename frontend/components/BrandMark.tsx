import type { BrandConfig } from "../branding/types";

type BrandMarkProps = {
  brand: BrandConfig;
};

export function BrandMark({ brand }: BrandMarkProps) {
  return (
    <div className="brand-mark" aria-label={brand.productName}>
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