import type { ProjectDto, ProjectSessionDto, SessionMemoryDto } from "../api/dtos";
import { createPlatformClients, type PlatformClients } from "../api";

type KnowledgeClients = Pick<PlatformClients, "projects" | "projectHistory">;

export interface KnowledgeLoader {
  listProjects(): Promise<readonly ProjectDto[]>;
  listSessions(projectId: string): Promise<readonly ProjectSessionDto[]>;
  listMemory(projectId: string, sessionId: string): Promise<readonly SessionMemoryDto[]>;
}

export class KnowledgeDataService implements KnowledgeLoader {
  constructor(private readonly clients: KnowledgeClients) {}

  listProjects(): Promise<readonly ProjectDto[]> {
    return this.clients.projects.list();
  }

  listSessions(projectId: string): Promise<readonly ProjectSessionDto[]> {
    return this.clients.projectHistory.listSessions(projectId);
  }

  listMemory(projectId: string, sessionId: string): Promise<readonly SessionMemoryDto[]> {
    return this.clients.projectHistory.listMemory(projectId, sessionId);
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
    listMemory: (projectId, sessionId) => getService().listMemory(projectId, sessionId),
  };
}
