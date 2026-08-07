import { createPlatformClients, type PlatformClients } from "../api";
import type { AIRuntimeStatusDto } from "../api/dtos";

export interface AIRuntimeSettingsService {
  codexStatus(): Promise<AIRuntimeStatusDto>;
}

export function createAIRuntimeSettingsService(
  clientsFactory: () => Pick<PlatformClients, "aiRuntimes"> = createPlatformClients,
): AIRuntimeSettingsService {
  let clients: Pick<PlatformClients, "aiRuntimes"> | undefined;
  return {
    codexStatus: () => (clients ??= clientsFactory()).aiRuntimes.status("codex"),
  };
}
