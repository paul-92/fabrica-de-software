import { createPlatformClients, type PlatformClients } from "../api";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto, ProjectEngineeringPreparationDto, ProjectExecutionDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind } from "../api/dtos";

export interface ProjectRuntimeWorkspaceService {
  status(): Promise<AIRuntimeStatusDto>;
  execute(projectId: string, sessionId: string, instruction: string, executionMode: AIRuntimeExecutionMode): Promise<ProjectAIRuntimeExecutionDto>;
  prepare(projectId: string, sessionId: string, instruction: string): Promise<ProjectEngineeringPreparationDto>;
  approve(projectId: string, preparationId: string, sessionId: string, instruction: string): Promise<ProjectAIRuntimeExecutionDto>;
  cancel(projectId: string, preparationId: string, sessionId: string, instruction: string): Promise<ProjectExecutionDto>;
  listSessions(projectId: string): Promise<readonly ProjectSessionDto[]>;
  createSession(projectId: string, title: string): Promise<ProjectSessionDto>;
  listExecutions(projectId: string, sessionId: string): Promise<readonly ProjectExecutionDto[]>;
  getExecution(projectId: string, executionId: string): Promise<ProjectExecutionDto>;
  listMemory(projectId: string, sessionId: string): Promise<readonly SessionMemoryDto[]>;
  addMemory(projectId: string, sessionId: string, kind: SessionMemoryKind, content: string): Promise<SessionMemoryDto>;
}

export function createProjectRuntimeWorkspaceService(
  clientsFactory: () => Pick<PlatformClients, "aiRuntimes" | "projectRuntime" | "projectHistory"> = createPlatformClients,
): ProjectRuntimeWorkspaceService {
  let clients: Pick<PlatformClients, "aiRuntimes" | "projectRuntime" | "projectHistory"> | undefined;
  const get = () => (clients ??= clientsFactory());
  return {
    status: () => get().aiRuntimes.status("codex"),
    execute: (projectId, sessionId, instruction, executionMode) => get().projectRuntime.execute(projectId, {
      session_id: sessionId, runtime_id: "codex", instruction, execution_mode: executionMode,
    }),
    prepare: (projectId, sessionId, instruction) => get().projectRuntime.prepare(projectId, { session_id: sessionId, runtime_id: "codex", instruction, execution_mode: "workspace_write" }),
    approve: (projectId, preparationId, sessionId, instruction) => get().projectRuntime.approve(projectId, preparationId, { session_id: sessionId, runtime_id: "codex", instruction, execution_mode: "workspace_write" }),
    cancel: (projectId, preparationId, sessionId, instruction) => get().projectRuntime.cancel(projectId, preparationId, { session_id: sessionId, runtime_id: "codex", instruction, execution_mode: "workspace_write" }),
    listSessions: (projectId) => get().projectHistory.listSessions(projectId),
    createSession: (projectId, title) => get().projectHistory.createSession(projectId, title),
    listExecutions: (projectId, sessionId) => get().projectHistory.listSessionExecutions(projectId, sessionId),
    getExecution: (projectId, executionId) => get().projectHistory.getExecution(projectId, executionId),
    listMemory: (projectId, sessionId) => get().projectHistory.listMemory(projectId, sessionId),
    addMemory: (projectId, sessionId, kind, content) => get().projectHistory.addMemory(projectId, sessionId, kind, content),
  };
}
