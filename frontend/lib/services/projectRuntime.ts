import { ApiClient } from "../api/client";
import type { AIRuntimeExecutionMode, JsonValue, ProjectAIRuntimeExecutionDto, ProjectExecutionDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind } from "../api/dtos";

export class ProjectRuntimeClient {
  constructor(private readonly api: ApiClient) {}
  execute(projectId: string, request: Readonly<{
    session_id: string;
    runtime_id: string;
    instruction: string;
    metadata?: Record<string, JsonValue>;
    execution_mode?: AIRuntimeExecutionMode;
  }>): Promise<ProjectAIRuntimeExecutionDto> {
    return this.api.request({
      path: `/api/v1/projects/${encodeURIComponent(projectId)}/ai-runtime/execute`,
      method: "POST",
      body: request,
    });
  }
}

type SessionsResponse = Readonly<{ items: readonly ProjectSessionDto[] }>;
type ExecutionsResponse = Readonly<{ items: readonly ProjectExecutionDto[] }>;
type MemoryResponse = Readonly<{ items: readonly SessionMemoryDto[] }>;

export class ProjectHistoryClient {
  constructor(private readonly api: ApiClient) {}
  async listSessions(projectId: string): Promise<readonly ProjectSessionDto[]> {
    return (await this.api.request<SessionsResponse>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions` })).items;
  }
  createSession(projectId: string, title: string): Promise<ProjectSessionDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions`, method: "POST", body: { title } });
  }
  async listSessionExecutions(projectId: string, sessionId: string): Promise<readonly ProjectExecutionDto[]> {
    return (await this.api.request<ExecutionsResponse>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/executions` })).items;
  }
  getExecution(projectId: string, executionId: string): Promise<ProjectExecutionDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(executionId)}` });
  }
  async listMemory(projectId: string, sessionId: string): Promise<readonly SessionMemoryDto[]> {
    return (await this.api.request<MemoryResponse>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/memory` })).items;
  }
  addMemory(projectId: string, sessionId: string, kind: SessionMemoryKind, content: string): Promise<SessionMemoryDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/memory`, method: "POST", body: { kind, content } });
  }
}
