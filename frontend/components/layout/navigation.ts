export type NavigationItem = Readonly<{
  label: string;
  href: string;
  icon: NavigationIcon;
}>;

export type NavigationIcon =
  | "dashboard"
  | "projects"
  | "executions"
  | "agents"
  | "planning"
  | "knowledge"
  | "quality"
  | "settings";

export const navigationItems: readonly NavigationItem[] = [
  { label: "Dashboard", href: "/", icon: "dashboard" },
  { label: "Projects", href: "/projects", icon: "projects" },
  { label: "Executions", href: "/executions", icon: "executions" },
  { label: "Agents", href: "/agents", icon: "agents" },
  { label: "Planning", href: "/planning", icon: "planning" },
  { label: "Knowledge", href: "/knowledge", icon: "knowledge" },
  { label: "Quality", href: "/quality", icon: "quality" },
  { label: "Settings", href: "/settings", icon: "settings" },
];

export function isNavigationItemActive(pathname: string, href: string) {
  return href === "/"
    ? pathname === href
    : pathname === href || pathname.startsWith(`${href}/`);
}

export function titleForPath(pathname: string) {
  return (
    navigationItems.find((item) => isNavigationItemActive(pathname, item.href))
      ?.label ?? "Workspace"
  );
}
