import { createPlatformClients, type PlatformClients } from "../api";
import { ApiClient } from "../api/client";
import type {
  AgentCatalogItemDto,
  AgentRuntimeProjectionDto,
} from "../api/dtos";

type AgentCatalogResponse = Readonly<{
  items: readonly AgentCatalogItemDto[];
}>;

type AgentRuntimeProjectionResponse = Readonly<{
  items: readonly AgentRuntimeProjectionDto[];
}>;

export class AgentsClient {
  constructor(private readonly api: ApiClient) {}

  async list(): Promise<readonly AgentCatalogItemDto[]> {
    return (
      await this.api.request<AgentCatalogResponse>({ path: "/api/v1/agents" })
    ).items;
  }

  async listRuntime(): Promise<readonly AgentRuntimeProjectionDto[]> {
    return (
      await this.api.request<AgentRuntimeProjectionResponse>({
        path: "/api/v1/agents/runtime",
      })
    ).items;
  }
}

type AgentsClients = Pick<PlatformClients, "agents">;

export interface AgentsLoader {
  listAgents(): Promise<readonly AgentCatalogItemDto[]>;
  listRuntime(): Promise<readonly AgentRuntimeProjectionDto[]>;
}

export class AgentsWorkspaceService implements AgentsLoader {
  constructor(private readonly clients: AgentsClients) {}

  async listAgents(): Promise<readonly AgentCatalogItemDto[]> {
    const items = await this.clients.agents.list();
    return [...items].sort((left, right) =>
      left.agent_id.localeCompare(right.agent_id),
    );
  }

  async listRuntime(): Promise<readonly AgentRuntimeProjectionDto[]> {
    const items = await this.clients.agents.listRuntime();
    return [...items].sort((left, right) =>
      left.agent_id.localeCompare(right.agent_id),
    );
  }
}

export function createAgentsLoader(
  clientsFactory: () => AgentsClients = createPlatformClients,
): AgentsLoader {
  let service: AgentsWorkspaceService | undefined;
  const getService = () =>
    (service ??= new AgentsWorkspaceService(clientsFactory()));
  return {
    listAgents: () => getService().listAgents(),
    listRuntime: () => getService().listRuntime(),
  };
}
