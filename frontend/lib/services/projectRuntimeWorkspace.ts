import { createPlatformClients, type PlatformClients } from "../api";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto } from "../api/dtos";

export interface ProjectRuntimeWorkspaceService {
  status(): Promise<AIRuntimeStatusDto>;
  execute(projectId: string, instruction: string, executionMode: AIRuntimeExecutionMode): Promise<ProjectAIRuntimeExecutionDto>;
}

export function createProjectRuntimeWorkspaceService(
  clientsFactory: () => Pick<PlatformClients, "aiRuntimes" | "projectRuntime"> = createPlatformClients,
): ProjectRuntimeWorkspaceService {
  let clients: Pick<PlatformClients, "aiRuntimes" | "projectRuntime"> | undefined;
  const get = () => (clients ??= clientsFactory());
  return {
    status: () => get().aiRuntimes.status("codex"),
    execute: (projectId, instruction, executionMode) => get().projectRuntime.execute(projectId, {
      runtime_id: "codex", instruction, execution_mode: executionMode,
    }),
  };
}
