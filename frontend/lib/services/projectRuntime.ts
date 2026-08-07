import { ApiClient } from "../api/client";
import type { JsonValue, ProjectAIRuntimeExecutionDto } from "../api/dtos";

export class ProjectRuntimeClient {
  constructor(private readonly api: ApiClient) {}
  execute(projectId: string, request: Readonly<{
    runtime_id: string;
    instruction: string;
    metadata?: Record<string, JsonValue>;
  }>): Promise<ProjectAIRuntimeExecutionDto> {
    return this.api.request({
      path: `/api/v1/projects/${encodeURIComponent(projectId)}/ai-runtime/execute`,
      method: "POST",
      body: request,
    });
  }
}
