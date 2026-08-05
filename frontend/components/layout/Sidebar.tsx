import Link from "next/link";

import type { BrandConfig } from "../../branding/types";
import { BrandMark } from "../BrandMark";
import { NavIcon } from "./NavIcon";
import { isNavigationItemActive, navigationItems } from "./navigation";

type SidebarProps = {
  brand: BrandConfig;
  pathname: string;
  mobileOpen: boolean;
  onNavigate: () => void;
};

export function Sidebar({
  brand,
  pathname,
  mobileOpen,
  onNavigate,
}: SidebarProps) {
  return (
    <aside
      className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`.trim()}
      aria-label="Navegação principal"
    >
      <div className="sidebar__brand">
        <BrandMark brand={brand} />
      </div>
      <nav className="sidebar__nav">
        {navigationItems.map((item) => {
          const active = isNavigationItemActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${active ? "nav-link--active" : ""}`.trim()}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
            >
              <NavIcon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <p className="sidebar__footer">Interface foundation</p>
    </aside>
  );
}
