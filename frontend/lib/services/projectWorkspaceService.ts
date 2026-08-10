import { createPlatformClients, type PlatformClients } from "../api";
import type { WorkspaceDirectoryDto, WorkspaceFileContentDto } from "../api/dtos";

export interface ProjectWorkspaceService {
  listDirectory(projectId: string, path?: string): Promise<WorkspaceDirectoryDto>;
  readFile(projectId: string, path: string): Promise<WorkspaceFileContentDto>;
}

export function createProjectWorkspaceService(
  clientsFactory: () => Pick<PlatformClients, "projectWorkspace"> = createPlatformClients,
): ProjectWorkspaceService {
  let clients: Pick<PlatformClients, "projectWorkspace"> | undefined;
  const get = () => (clients ??= clientsFactory()).projectWorkspace;
  return { listDirectory: (projectId, path) => get().listDirectory(projectId, path), readFile: (projectId, path) => get().readFile(projectId, path) };
}
