import type { MetricsSummaryDto, RunDto } from "../api/dtos";
import {
  createPlatformClients,
  type PlatformClients,
} from "../api";

export type DashboardData = Readonly<{
  metrics: MetricsSummaryDto;
  recentRuns: readonly RunDto[];
}>;

export interface DashboardLoader {
  load(): Promise<DashboardData>;
}

export class DashboardDataService implements DashboardLoader {
  constructor(
    private readonly clients: Pick<PlatformClients, "runs" | "metrics">,
    private readonly recentRunsLimit = 8,
  ) {}

  async load(): Promise<DashboardData> {
    const [metrics, runs] = await Promise.all([
      this.clients.metrics.summary(),
      this.clients.runs.list(),
    ]);
    return {
      metrics,
      recentRuns: runs.slice(0, this.recentRunsLimit),
    };
  }
}

export function createDashboardLoader(
  clientsFactory: () => PlatformClients = createPlatformClients,
): DashboardLoader {
  return {
    async load() {
      return new DashboardDataService(clientsFactory()).load();
    },
  };
}
