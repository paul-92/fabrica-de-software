import type { CreateProjectDto, ProjectDto } from "../api/dtos";
import { ApiClient } from "../api/client";

type ProjectListResponse = Readonly<{ items: readonly ProjectDto[] }>;

export class ProjectsClient {
  constructor(private readonly api: ApiClient) {}
  async list(): Promise<readonly ProjectDto[]> {
    return (await this.api.request<ProjectListResponse>({ path: "/api/v1/projects" })).items;
  }
  create(request: CreateProjectDto): Promise<ProjectDto> {
    return this.api.request<ProjectDto>({ path: "/api/v1/projects", method: "POST", body: request });
  }
  get(projectId: string): Promise<ProjectDto> {
    return this.api.request<ProjectDto>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}` });
  }
}
