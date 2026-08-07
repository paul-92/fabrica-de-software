import { createPlatformClients, type PlatformClients } from "../api";
import type { CreateProjectDto, ProjectDto } from "../api/dtos";
import type { ProjectsClient } from "./projects";

export interface ProjectsWorkspaceService {
  list(): Promise<readonly ProjectDto[]>;
  create(request: CreateProjectDto): Promise<ProjectDto>;
  get(projectId: string): Promise<ProjectDto>;
}

export function createProjectsWorkspaceService(
  clientsFactory: () => Pick<PlatformClients, "projects"> = createPlatformClients,
): ProjectsWorkspaceService {
  let client: ProjectsClient | undefined;
  const getClient = () => (client ??= clientsFactory().projects);
  return {
    list: () => getClient().list(),
    create: (request) => getClient().create(request),
    get: (projectId) => getClient().get(projectId),
  };
}
