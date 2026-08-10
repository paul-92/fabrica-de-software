import { describe, expect, it, vi } from "vitest";
import type { MetricsSummaryDto, ProviderMetricDto, RunDto, StatusMetricDto } from "../api/dtos";
import type { PlatformClients } from "../api";
import { QualityDataService } from "./quality";

const summary = { total_runs: 3 } as MetricsSummaryDto;
const statuses = [{ status: "succeeded", count: 2 }] as readonly StatusMetricDto[];
const providers: readonly ProviderMetricDto[] = [{
  provider_name: "codex",
  total_runs: 3,
  successful_runs: 2,
  failed_runs: 1,
  running_runs: 0,
  unknown_status_runs: 0,
  eligible_runs: 3,
  success_rate: 66.7,
  failure_rate: 33.3,
  duration: {
    count: 3,
    ignored_count: 0,
    minimum_seconds: 1,
    maximum_seconds: 3,
    average_seconds: 2,
    median_seconds: 2,
  },
}];
const run = (id: string, startedAt: string): RunDto => ({ id, started_at: startedAt } as RunDto);

describe("QualityDataService", () => {
  it("aggregates public metrics and limits recent runs in chronological order", async () => {
    const clients = {
      metrics: {
        summary: vi.fn().mockResolvedValue(summary),
        byStatus: vi.fn().mockResolvedValue(statuses),
        byProvider: vi.fn().mockResolvedValue(providers),
      },
      runs: { list: vi.fn().mockResolvedValue([
        run("older", "2026-08-01T10:00:00Z"),
        run("newer", "2026-08-03T10:00:00Z"),
        run("middle", "2026-08-02T10:00:00Z"),
      ]) },
    } as unknown as Pick<PlatformClients, "metrics" | "runs">;

    const result = await new QualityDataService(clients, 2).load();

    expect(clients.metrics.summary).toHaveBeenCalledOnce();
    expect(clients.metrics.byStatus).toHaveBeenCalledOnce();
    expect(clients.metrics.byProvider).toHaveBeenCalledOnce();
    expect(clients.runs.list).toHaveBeenCalledOnce();
    expect(result).toEqual({ summary, statuses, providers, recentRuns: [
      expect.objectContaining({ id: "newer" }),
      expect.objectContaining({ id: "middle" }),
    ] });
  });
});
