import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { PlatformClients } from "../api";
import type { AgentCatalogItemDto } from "../api/dtos";
import { AgentsWorkspaceService, createAgentsLoader } from "./agents";

const agent = (agentId: string): AgentCatalogItemDto => ({
  agent_id: agentId,
  name: agentId,
  version: "0.1.0",
  lifecycle_status: "active",
  department: "Engineering",
  capabilities: [],
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
    const clientsFactory = vi.fn().mockReturnValue({ agents: { list } });
    const loader = createAgentsLoader(clientsFactory);

    expect(clientsFactory).not.toHaveBeenCalled();
    await loader.listAgents();
    await loader.listAgents();

    expect(clientsFactory).toHaveBeenCalledOnce();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it("does not depend on runtime, Codex, registry or Core contracts", () => {
    const source = readFileSync(new URL("./agents.ts", import.meta.url), "utf8");
    for (const forbidden of ["runtime", "codex", "registry", "asep.agents", "core/"]) {
      expect(source.toLowerCase()).not.toContain(forbidden);
    }
  });
});
