import { ApiClient } from "../api/client";
import type { AIUsageResponseDto } from "../api/dtos";
import type { AIRuntimeExecutionMode, JsonValue, ProjectAIRuntimeExecutionDto, ProjectEngineeringPreparationDto, ProjectExecutionDto, ProjectLifecycleDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind, SessionMemorySearchPageDto, SessionMemorySearchParams, StructuredEngineeringContextDto } from "../api/dtos";

export const AI_OPERATION_TIMEOUT_MS = 600_000;

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
      timeoutMs: AI_OPERATION_TIMEOUT_MS,
    });
  }
  prepare(projectId: string, request: Readonly<{ session_id: string; runtime_id: string; instruction: string; execution_mode: "workspace_write" } & StructuredEngineeringContextDto>): Promise<ProjectEngineeringPreparationDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/engineering/prepare`, method: "POST", body: request, timeoutMs: AI_OPERATION_TIMEOUT_MS });
  }
  approve(projectId: string, preparationId: string, request: Readonly<{ session_id: string; runtime_id: string; instruction: string; execution_mode: "workspace_write" } & StructuredEngineeringContextDto>): Promise<ProjectAIRuntimeExecutionDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/engineering/${encodeURIComponent(preparationId)}/approve`, method: "POST", body: request, timeoutMs: AI_OPERATION_TIMEOUT_MS });
  }
  cancel(projectId: string, preparationId: string, request: Readonly<{ session_id: string; runtime_id: string; instruction: string; execution_mode: "workspace_write" }>): Promise<ProjectExecutionDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/engineering/${encodeURIComponent(preparationId)}/cancel`, method: "POST", body: request });
  }
  approveDependency(projectId: string, requestId: string, expectedVersion = 1): Promise<unknown> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/dependency-requests/${encodeURIComponent(requestId)}/approve`, method: "POST", body: { expected_version: expectedVersion } });
  }

  selectDependencyVersion(
    projectId: string,
    preparationId: string,
    packageName: string,
    version: string,
  ): Promise<ProjectExecutionDto> {
    return this.api.request({
      path: `/api/v1/projects/${encodeURIComponent(projectId)}/engineering/${encodeURIComponent(preparationId)}/dependencies/${encodeURIComponent(packageName)}/version`,
      method: "POST",
      body: { version },
    });
  }
  rejectDependency(projectId: string, requestId: string, expectedVersion = 1): Promise<unknown> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/dependency-requests/${encodeURIComponent(requestId)}/reject`, method: "POST", body: { expected_version: expectedVersion } });
  }
}

type SessionsResponse = Readonly<{ items: readonly ProjectSessionDto[] }>;
type ExecutionsResponse = Readonly<{ items: readonly ProjectExecutionDto[] }>;
type MemoryResponse = Readonly<{ items: readonly SessionMemoryDto[] }>;

export class ProjectHistoryClient {
  constructor(private readonly api: ApiClient) {}
  getLifecycle(projectId:string):Promise<ProjectLifecycleDto> { return this.api.request({path:`/api/v1/projects/${encodeURIComponent(projectId)}/lifecycle`}); }
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
  getExecutionUsage(projectId: string, executionId: string): Promise<AIUsageResponseDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/executions/${encodeURIComponent(executionId)}/ai-usage` });
  }
  async listMemory(projectId: string, sessionId: string): Promise<readonly SessionMemoryDto[]> {
    return (await this.api.request<MemoryResponse>({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/memory` })).items;
  }
  searchMemory(projectId: string, sessionId: string, params: SessionMemorySearchParams = {}): Promise<SessionMemorySearchPageDto> {
    const query = new URLSearchParams();
    if (params.text !== undefined) query.set("text", params.text);
    if (params.kind !== undefined) query.set("kind", params.kind);
    if (params.order !== undefined) query.set("order", params.order);
    if (params.page_size !== undefined) query.set("page_size", String(params.page_size));
    if (params.cursor !== undefined) query.set("cursor", params.cursor);
    const suffix = query.size > 0 ? `?${query.toString()}` : "";
    return this.api.request({
      path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/memory/search${suffix}`,
    });
  }
  addMemory(projectId: string, sessionId: string, kind: SessionMemoryKind, content: string): Promise<SessionMemoryDto> {
    return this.api.request({ path: `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/memory`, method: "POST", body: { kind, content } });
  }
}
