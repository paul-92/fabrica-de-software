import { ApiClient } from "../api/client";
import type { WorkspaceDirectoryDto, WorkspaceFileContentDto } from "../api/dtos";

export class ProjectWorkspaceClient {
  constructor(private readonly api: ApiClient) {}
  listDirectory(projectId: string, path = ""): Promise<WorkspaceDirectoryDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/workspace?path=${encodeURIComponent(path)}` });
  }
  readFile(projectId: string, path: string): Promise<WorkspaceFileContentDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/workspace/file?path=${encodeURIComponent(path)}` });
  }
}
