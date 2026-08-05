type Status = "success" | "warning" | "danger" | "neutral";

type StatusBadgeProps = {
  children: string;
  status?: Status;
};

export function StatusBadge({
  children,
  status = "neutral",
}: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${status}`}>{children}</span>;
}
