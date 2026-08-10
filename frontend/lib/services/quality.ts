import type {
  MetricsSummaryDto,
  ProviderMetricDto,
  RunDto,
  StatusMetricDto,
} from "../api/dtos";
import { createPlatformClients, type PlatformClients } from "../api";

type QualityClients = Pick<PlatformClients, "metrics" | "runs">;

export type QualityData = Readonly<{
  summary: MetricsSummaryDto;
  statuses: readonly StatusMetricDto[];
  providers: readonly ProviderMetricDto[];
  recentRuns: readonly RunDto[];
}>;

export interface QualityLoader {
  load(): Promise<QualityData>;
}

export class QualityDataService implements QualityLoader {
  constructor(
    private readonly clients: QualityClients,
    private readonly recentRunsLimit = 8,
  ) {}

  async load(): Promise<QualityData> {
    const [summary, statuses, providers, runs] = await Promise.all([
      this.clients.metrics.summary(),
      this.clients.metrics.byStatus(),
      this.clients.metrics.byProvider(),
      this.clients.runs.list(),
    ]);
    const recentRuns = [...runs]
      .sort((left, right) => Date.parse(right.started_at) - Date.parse(left.started_at))
      .slice(0, this.recentRunsLimit);
    return { summary, statuses, providers, recentRuns };
  }
}

export function createQualityLoader(
  clientsFactory: () => QualityClients = createPlatformClients,
): QualityLoader {
  let service: QualityDataService | undefined;
  const getService = () => (service ??= new QualityDataService(clientsFactory()));
  return { load: () => getService().load() };
}
