import type { ProjectDto, ProjectSessionDto, SessionMemorySearchPageDto, SessionMemorySearchParams } from "../api/dtos";
import { createPlatformClients, type PlatformClients } from "../api";

type KnowledgeClients = Pick<PlatformClients, "projects" | "projectHistory">;

export interface KnowledgeLoader {
  listProjects(): Promise<readonly ProjectDto[]>;
  listSessions(projectId: string): Promise<readonly ProjectSessionDto[]>;
  searchMemory(projectId: string, sessionId: string, params?: SessionMemorySearchParams): Promise<SessionMemorySearchPageDto>;
}

export class KnowledgeDataService implements KnowledgeLoader {
  constructor(private readonly clients: KnowledgeClients) {}

  listProjects(): Promise<readonly ProjectDto[]> {
    return this.clients.projects.list();
  }

  listSessions(projectId: string): Promise<readonly ProjectSessionDto[]> {
    return this.clients.projectHistory.listSessions(projectId);
  }

  searchMemory(projectId: string, sessionId: string, params: SessionMemorySearchParams = {}): Promise<SessionMemorySearchPageDto> {
    return this.clients.projectHistory.searchMemory(projectId, sessionId, params);
  }
}

export function createKnowledgeLoader(
  clientsFactory: () => KnowledgeClients = createPlatformClients,
): KnowledgeLoader {
  let service: KnowledgeDataService | undefined;
  const getService = () => (service ??= new KnowledgeDataService(clientsFactory()));
  return {
    listProjects: () => getService().listProjects(),
    listSessions: (projectId) => getService().listSessions(projectId),
    searchMemory: (projectId, sessionId, params) => getService().searchMemory(projectId, sessionId, params),
  };
}
