import { ApiClient } from "../api/client";
import type {
  MetricsSummaryDto,
  ProviderMetricDto,
  StatusMetricDto,
} from "../api/dtos";

type StatusMetricsResponse = Readonly<{ items: readonly StatusMetricDto[] }>;
type ProviderMetricsResponse = Readonly<{ items: readonly ProviderMetricDto[] }>;

export class MetricsClient {
  constructor(private readonly api: ApiClient) {}

  summary(signal?: AbortSignal): Promise<MetricsSummaryDto> {
    return this.api.request<MetricsSummaryDto>({
      path: "/api/v1/metrics/summary",
      signal,
    });
  }

  async byStatus(signal?: AbortSignal): Promise<readonly StatusMetricDto[]> {
    return (
      await this.api.request<StatusMetricsResponse>({
        path: "/api/v1/metrics/status",
        signal,
      })
    ).items;
  }

  async byProvider(
    signal?: AbortSignal,
  ): Promise<readonly ProviderMetricDto[]> {
    return (
      await this.api.request<ProviderMetricsResponse>({
        path: "/api/v1/metrics/providers",
        signal,
      })
    ).items;
  }
}
