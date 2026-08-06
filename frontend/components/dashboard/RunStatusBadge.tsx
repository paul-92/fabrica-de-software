import { StatusBadge } from "../StatusBadge";

const statusPresentation = {
  succeeded: { label: "Succeeded", tone: "success" },
  completed: { label: "Completed", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  running: { label: "Running", tone: "warning" },
  pending: { label: "Pending", tone: "neutral" },
  cancelled: { label: "Cancelled", tone: "neutral" },
} as const;

export function RunStatusBadge({ status }: { status: string }) {
  const presentation =
    statusPresentation[status as keyof typeof statusPresentation] ?? {
      label: status,
      tone: "neutral" as const,
    };
  return (
    <StatusBadge status={presentation.tone}>{presentation.label}</StatusBadge>
  );
}
