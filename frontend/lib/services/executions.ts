import type { RunDto, TimelineEventDto } from "../api/dtos";
import { createPlatformClients, type PlatformClients } from "../api";

type ExecutionsClients = Readonly<{
  runs: Pick<PlatformClients["runs"], "list" | "get" | "timeline">;
}>;

export interface ExecutionsLoader {
  list(): Promise<readonly RunDto[]>;
  get(runId: string): Promise<RunDto>;
  timeline(runId: string): Promise<readonly TimelineEventDto[]>;
}

export class ExecutionsDataService implements ExecutionsLoader {
  constructor(
    private readonly runs: Pick<PlatformClients["runs"], "list" | "get" | "timeline">,
  ) {}

  async list(): Promise<readonly RunDto[]> {
    const runs = await this.runs.list();
    return [...runs].sort((left, right) => {
      const byStartedAt = Date.parse(right.started_at) - Date.parse(left.started_at);
      return byStartedAt || left.id.localeCompare(right.id);
    });
  }

  get(runId: string): Promise<RunDto> { return this.runs.get(runId); }
  timeline(runId: string): Promise<readonly TimelineEventDto[]> { return this.runs.timeline(runId); }
}

export function createExecutionsLoader(clientsFactory: () => ExecutionsClients = createPlatformClients): ExecutionsLoader {
  let service: ExecutionsDataService | undefined;
  const getService = () => {
    service ??= new ExecutionsDataService(clientsFactory().runs);
    return service;
  };
  return {
    list: () => getService().list(),
    get: (runId) => getService().get(runId),
    timeline: (runId) => getService().timeline(runId),
  };
}
