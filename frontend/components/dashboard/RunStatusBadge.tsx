import { StatusBadge } from "../StatusBadge";

const statusPresentation = {
  succeeded: { label: "Concluído", tone: "success" },
  completed: { label: "Concluído", tone: "success" },
  failed: { label: "Falhou", tone: "danger" },
  running: { label: "Executando", tone: "warning" },
  pending: { label: "Pendente", tone: "neutral" },
  cancelled: { label: "Cancelado", tone: "neutral" },
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
