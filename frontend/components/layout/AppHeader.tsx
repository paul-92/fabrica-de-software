import type { BrandConfig } from "../../branding/types";
import { ThemeToggle } from "../ThemeToggle";

type AppHeaderProps = {
  title: string;
  brand: BrandConfig;
  onOpenNavigation: () => void;
};

export function AppHeader({
  title,
  brand,
  onOpenNavigation,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__context">
        <button
          className="menu-button"
          type="button"
          aria-label="Abrir navegação"
          onClick={onOpenNavigation}
        >
          <span />
          <span />
          <span />
        </button>

        <div>
          <p className="app-header__eyebrow">{brand.workspaceLabel}</p>
          <p className="app-header__title">{title}</p>
        </div>
      </div>

      <div className="app-header__actions" aria-label="Ações globais">
        <ThemeToggle defaultTheme={brand.defaultTheme} />
      </div>
    </header>
  );
}