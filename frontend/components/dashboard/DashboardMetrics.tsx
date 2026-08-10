import type { MetricsSummaryDto } from "../../lib/api/dtos";
import { MetricCard } from "./MetricCard";

function formatDuration(seconds: number | null) {
  if (seconds === null) return "Indisponível";
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  return `${(seconds / 60).toFixed(1)} min`;
}

export function DashboardMetrics({ metrics }: { metrics: MetricsSummaryDto }) {
  return (
    <section className="dashboard-metrics" aria-label="Métricas de execução">
      <MetricCard label="Total" value={String(metrics.total_runs)} />
      <MetricCard label="Concluídas" value={String(metrics.successful_runs)} />
      <MetricCard label="Falhas" value={String(metrics.failed_runs)} />
      <MetricCard label="Executando" value={String(metrics.running_runs)} />
      <MetricCard label="Pendentes" value={String(metrics.pending_runs)} />
      <MetricCard
        label="Duração média"
        value={formatDuration(metrics.duration.average_seconds)}
        detail={`${metrics.duration.count} execuções medidas`}
      />
    </section>
  );
}
