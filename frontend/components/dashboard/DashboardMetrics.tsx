import type { MetricsSummaryDto } from "../../lib/api/dtos";
import { MetricCard } from "./MetricCard";

function formatDuration(seconds: number | null) {
  if (seconds === null) return "Unavailable";
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  return `${(seconds / 60).toFixed(1)} min`;
}

export function DashboardMetrics({ metrics }: { metrics: MetricsSummaryDto }) {
  return (
    <section className="dashboard-metrics" aria-label="Execution metrics">
      <MetricCard label="Total runs" value={String(metrics.total_runs)} />
      <MetricCard label="Succeeded" value={String(metrics.successful_runs)} />
      <MetricCard label="Failed" value={String(metrics.failed_runs)} />
      <MetricCard label="Running" value={String(metrics.running_runs)} />
      <MetricCard label="Pending" value={String(metrics.pending_runs)} />
      <MetricCard
        label="Average duration"
        value={formatDuration(metrics.duration.average_seconds)}
        detail={`${metrics.duration.count} measured runs`}
      />
    </section>
  );
}
