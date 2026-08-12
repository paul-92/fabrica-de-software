import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";
import type { PlatformClients } from "../api";
import type { SequentialQualityGateDto } from "../api/dtos";
import {
  SequentialQualityClient,
  SequentialQualityService,
} from "./sequentialQuality";

const gate: SequentialQualityGateDto = {
  gate_id: "QG-ANALYSIS",
  execution_id: "execution/one",
  stage_id: "analysis",
  decision: "APPROVED_WITH_PENDING",
  satisfied_criteria: ["Escopo definido"],
  unsatisfied_criteria: ["Revisão pendente"],
  evaluated_at: "2026-08-11T12:00:00Z",
};

describe("SequentialQualityClient", () => {
  it("requests the encoded public endpoint and parses canonical items", async () => {
    const request = vi.fn().mockResolvedValue({ items: [gate] });
    const client = new SequentialQualityClient(
      { request } as unknown as ApiClient,
    );

    await expect(client.list("project one/á", "execution/one")).resolves.toEqual([gate]);
    expect(request).toHaveBeenCalledWith({
      path: "/api/v1/sequential-projects/project%20one%2F%C3%A1/executions/execution%2Fone/quality-gates",
    });
  });

  it("preserves an empty public collection", async () => {
    const client = new SequentialQualityClient({
      request: vi.fn().mockResolvedValue({ items: [] }),
    } as unknown as ApiClient);
    await expect(client.list("project", "execution")).resolves.toEqual([]);
  });

  it("consumes the canonical backend enum representation without normalization", async () => {
    const client = new SequentialQualityClient({
      request: vi.fn().mockResolvedValue({
        items: [gate],
      }),
    } as unknown as ApiClient);
    await expect(client.list("project", "execution")).resolves.toEqual([gate]);
  });

  it("rejects non-canonical lowercase decision values", async () => {
    const client = new SequentialQualityClient({
      request: vi.fn().mockResolvedValue({
        items: [{ ...gate, decision: "approved_with_pending" }],
      }),
    } as unknown as ApiClient);
    await expect(client.list("project", "execution")).rejects.toMatchObject({
      name: "ApiResponseError",
    });
  });

  it("rejects unsupported decision values", async () => {
    const client = new SequentialQualityClient({
      request: vi.fn().mockResolvedValue({
        items: [{ ...gate, decision: "healthy" }],
      }),
    } as unknown as ApiClient);
    await expect(client.list("project", "execution")).rejects.toMatchObject({
      name: "ApiResponseError",
    });
  });

  it("propagates HTTP client failures", async () => {
    const failure = new Error("unavailable");
    const client = new SequentialQualityClient({
      request: vi.fn().mockRejectedValue(failure),
    } as unknown as ApiClient);
    await expect(client.list("project", "execution")).rejects.toBe(failure);
  });
});

describe("SequentialQualityService", () => {
  it("delegates identifiers without treating them as public projects or runs", async () => {
    const list = vi.fn().mockResolvedValue([gate]);
    const service = new SequentialQualityService({
      sequentialQuality: { list },
    } as unknown as Pick<PlatformClients, "sequentialQuality">);
    await expect(service.load("sequential-project", "sequential-execution"))
      .resolves.toEqual([gate]);
    expect(list).toHaveBeenCalledWith("sequential-project", "sequential-execution");
  });
});
