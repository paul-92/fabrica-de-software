import { describe, expect, it, vi } from "vitest";

import type { MetricsSummaryDto, RunDto } from "../api/dtos";
import type { PlatformClients } from "../api";
import { DashboardDataService } from "./dashboard";

const summary = { total_runs: 3 } as MetricsSummaryDto;

function run(id: string): RunDto {
  return { id } as RunDto;
}

describe("DashboardDataService", () => {
  it("loads runs and metrics once and applies the visual limit", async () => {
    const list = vi.fn().mockResolvedValue([run("one"), run("two"), run("three")]);
    const metrics = vi.fn().mockResolvedValue(summary);
    const clients = {
      runs: { list },
      metrics: { summary: metrics },
    } as unknown as Pick<PlatformClients, "runs" | "metrics">;

    const result = await new DashboardDataService(clients, 2).load();

    expect(list).toHaveBeenCalledOnce();
    expect(metrics).toHaveBeenCalledOnce();
    expect(result.metrics).toBe(summary);
    expect(result.recentRuns.map(({ id }) => id)).toEqual(["one", "two"]);
  });
});
