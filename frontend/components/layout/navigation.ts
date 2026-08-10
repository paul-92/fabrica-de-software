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
  { label: "Visão geral", href: "/", icon: "dashboard" },
  { label: "Projetos", href: "/projects", icon: "projects" },
  { label: "Execuções", href: "/executions", icon: "executions" },
  { label: "Agentes", href: "/agents", icon: "agents" },
  { label: "Planejamento", href: "/planning", icon: "planning" },
  { label: "Conhecimento", href: "/knowledge", icon: "knowledge" },
  { label: "Qualidade", href: "/quality", icon: "quality" },
  { label: "Configurações", href: "/settings", icon: "settings" },
];

export function isNavigationItemActive(pathname: string, href: string) {
  return href === "/"
    ? pathname === href
    : pathname === href || pathname.startsWith(`${href}/`);
}

export function titleForPath(pathname: string) {
  return (
    navigationItems.find((item) => isNavigationItemActive(pathname, item.href))
      ?.label ?? "Área de trabalho"
  );
}
