import type { NavigationIcon } from "./navigation";

const paths: Record<NavigationIcon, string> = {
  dashboard: "M4 4h6v6H4V4Zm10 0h6v10h-6V4ZM4 14h6v6H4v-6Zm10 4h6v2h-6v-2Z",
  projects: "M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v8A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-10Z",
  executions: "m9 7 7 5-7 5V7Zm-5 5a8 8 0 1 0 16 0 8 8 0 0 0-16 0Z",
  agents: "M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8 2a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 21a6 6 0 0 1 12 0H2Zm11.5 0a5 5 0 0 1 9 0h-9Z",
  planning: "M5 3h14v18H5V3Zm4 4h6M9 11h6M9 15h4",
  knowledge: "M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21V5.5ZM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21V5.5Z",
  quality: "m12 3 2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8L12 3Z",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-5 1 2.2 2.4.6 2-1.2 2 2-1.2 2 .6 2.4L21 12l-2.2 1 .6 2.4 1.2 2-2 2-2-1.2-2.4.6L12 21l-1-2.2-2.4-.6-2 1.2-2-2 1.2-2-.6-2.4L3 12l2.2-1-.6-2.4-1.2-2 2-2 2 1.2 2.4-.6L12 3Z",
};

export function NavIcon({ name }: { name: NavigationIcon }) {
  return (
    <svg
      aria-hidden="true"
      className="nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  );
}
