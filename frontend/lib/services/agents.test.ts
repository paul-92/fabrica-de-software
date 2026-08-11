import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { PlatformClients } from "../api";
import { ApiClient } from "../api/client";
import type {
  AgentCatalogItemDto,
  AgentRuntimeProjectionDto,
} from "../api/dtos";
import {
  AgentsClient,
  AgentsWorkspaceService,
  createAgentsLoader,
} from "./agents";

const agent = (agentId: string): AgentCatalogItemDto => ({
  agent_id: agentId,
  name: agentId,
  version: "0.1.0",
  lifecycle_status: "active",
  department: "Engineering",
  capabilities: [],
});

const runtime = (agentId: string): AgentRuntimeProjectionDto => ({
  agent_id: agentId,
  registered: true,
  execution_count: 3,
  succeeded: 2,
  failed: 1,
  rejected: 0,
  cancelled: 0,
  timed_out: 0,
  retries: 1,
});

describe("AgentsWorkspaceService", () => {
  it("delegates to the public client and returns deterministic ordering", async () => {
    const list = vi.fn().mockResolvedValue([agent("zeta"), agent("alpha")]);
    const clients = { agents: { list } } as unknown as Pick<
      PlatformClients,
      "agents"
    >;
    const service = new AgentsWorkspaceService(clients);

    const result = await service.listAgents();

    expect(list).toHaveBeenCalledOnce();
    expect(result.map((item) => item.agent_id)).toEqual(["alpha", "zeta"]);
  });

  it("initializes platform clients lazily and only once", async () => {
    const list = vi.fn().mockResolvedValue([]);
    const listRuntime = vi.fn().mockResolvedValue([]);
    const clientsFactory = vi.fn().mockReturnValue({
      agents: { list, listRuntime },
    });
    const loader = createAgentsLoader(clientsFactory);

    expect(clientsFactory).not.toHaveBeenCalled();
    await loader.listAgents();
    await loader.listAgents();

    expect(clientsFactory).toHaveBeenCalledOnce();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it("loads runtime data and preserves deterministic ordering", async () => {
    const listRuntime = vi.fn().mockResolvedValue([
      runtime("zeta"),
      runtime("alpha"),
    ]);
    const clients = {
      agents: { list: vi.fn(), listRuntime },
    } as unknown as Pick<PlatformClients, "agents">;

    const result = await new AgentsWorkspaceService(clients).listRuntime();

    expect(listRuntime).toHaveBeenCalledOnce();
    expect(result.map((item) => item.agent_id)).toEqual(["alpha", "zeta"]);
  });

  it("depends only on public HTTP contracts", () => {
    const source = readFileSync(new URL("./agents.ts", import.meta.url), "utf8");
    for (const forbidden of ["codex", "registry", "asep.agents", "core/", "python"]) {
      expect(source.toLowerCase()).not.toContain(forbidden);
    }
  });
});

describe("AgentsClient runtime projection", () => {
  it("requests the versioned runtime path and parses items", async () => {
    const request = vi.fn().mockResolvedValue({ items: [runtime("reviewer")] });
    const client = new AgentsClient(
      { request } as unknown as ApiClient,
    );

    await expect(client.listRuntime()).resolves.toEqual([runtime("reviewer")]);
    expect(request).toHaveBeenCalledWith({ path: "/api/v1/agents/runtime" });
  });

  it("propagates HTTP client failures", async () => {
    const failure = new Error("runtime unavailable");
    const client = new AgentsClient(
      {
        request: vi.fn().mockRejectedValue(failure),
      } as unknown as ApiClient,
    );

    await expect(client.listRuntime()).rejects.toBe(failure);
  });
});
