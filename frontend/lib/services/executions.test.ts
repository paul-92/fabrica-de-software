import { describe, expect, it, vi } from "vitest";
import type { RunDto } from "../api/dtos";
import { createExecutionsLoader, ExecutionsDataService } from "./executions";

function run(id: string, startedAt: string): RunDto {
  return { id, status: "completed", started_at: startedAt, finished_at: null, project_id: null, workflow_id: null, stage_id: null, provider_name: null, summary: null, error: null, metadata: {} };
}

describe("ExecutionsDataService", () => {
  it("sorts executions newest first without mutating the API response", async () => {
    const source = [run("older", "2026-08-04T10:00:00Z"), run("newer", "2026-08-05T10:00:00Z")];
    const runs = { list: vi.fn().mockResolvedValue(source), get: vi.fn(), timeline: vi.fn() };

    const result = await new ExecutionsDataService(runs).list();

    expect(result.map(({ id }) => id)).toEqual(["newer", "older"]);
    expect(source.map(({ id }) => id)).toEqual(["older", "newer"]);
  });

  it("delegates detail and timeline with the exact run id", async () => {
    const detail = run("run/a ?", "2026-08-05T10:00:00Z");
    const runs = { list: vi.fn(), get: vi.fn().mockResolvedValue(detail), timeline: vi.fn().mockResolvedValue([]) };
    const service = new ExecutionsDataService(runs);

    await service.get("run/a ?");
    await service.timeline("run/a ?");

    expect(runs.get).toHaveBeenCalledWith("run/a ?");
    expect(runs.timeline).toHaveBeenCalledWith("run/a ?");
  });

  it("defers API client creation until the first request", async () => {
    const clientsFactory = vi.fn(() => ({
      runs: { list: vi.fn().mockResolvedValue([]), get: vi.fn(), timeline: vi.fn() },
    }));

    const loader = createExecutionsLoader(clientsFactory);
    expect(clientsFactory).not.toHaveBeenCalled();

    await loader.list();
    expect(clientsFactory).toHaveBeenCalledOnce();
  });
});
