import { createPlatformClients, type PlatformClients } from "../api";
import { ApiClient } from "../api/client";
import { ApiResponseError } from "../api/errors";
import type {
  SequentialQualityGateDecision,
  SequentialQualityGateDto,
} from "../api/dtos";

type SequentialQualityGateResponse = Readonly<{
  items: readonly (Omit<SequentialQualityGateDto, "decision"> & {
    decision: string;
  })[];
}>;

export class SequentialQualityClient {
  constructor(private readonly api: ApiClient) {}

  async list(
    projectId: string,
    executionId: string,
  ): Promise<readonly SequentialQualityGateDto[]> {
    const project = encodeURIComponent(projectId);
    const execution = encodeURIComponent(executionId);
    const response = await this.api.request<SequentialQualityGateResponse>({
        path: `/api/v1/sequential-projects/${project}/executions/${execution}/quality-gates`,
    });
    return response.items.map((item) => ({
      gate_id: item.gate_id,
      execution_id: item.execution_id,
      stage_id: item.stage_id,
      decision: parseDecision(item.decision),
      satisfied_criteria: item.satisfied_criteria,
      unsatisfied_criteria: item.unsatisfied_criteria,
      evaluated_at: item.evaluated_at,
    }));
  }
}

function parseDecision(value: string): SequentialQualityGateDecision {
  if (
    value === "APPROVED"
    || value === "APPROVED_WITH_PENDING"
    || value === "BLOCKED"
  ) return value;
  throw new ApiResponseError("API returned an unsupported Quality Gate decision.");
}

type SequentialQualityClients = Pick<PlatformClients, "sequentialQuality">;

export interface SequentialQualityLoader {
  load(
    projectId: string,
    executionId: string,
  ): Promise<readonly SequentialQualityGateDto[]>;
}

export class SequentialQualityService implements SequentialQualityLoader {
  constructor(private readonly clients: SequentialQualityClients) {}

  load(
    projectId: string,
    executionId: string,
  ): Promise<readonly SequentialQualityGateDto[]> {
    return this.clients.sequentialQuality.list(projectId, executionId);
  }
}

export function createSequentialQualityLoader(
  clientsFactory: () => SequentialQualityClients = createPlatformClients,
): SequentialQualityLoader {
  let service: SequentialQualityService | undefined;
  const getService = () =>
    (service ??= new SequentialQualityService(clientsFactory()));
  return {
    load: (projectId, executionId) =>
      getService().load(projectId, executionId),
  };
}
