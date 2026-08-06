import { ApiClient } from "../api/client";
import type { RunDto, TimelineEventDto } from "../api/dtos";

type RunListResponse = Readonly<{ items: readonly RunDto[] }>;
type TimelineResponse = Readonly<{ items: readonly TimelineEventDto[] }>;

export class RunsClient {
  constructor(private readonly api: ApiClient) {}

  async list(signal?: AbortSignal): Promise<readonly RunDto[]> {
    return (await this.api.request<RunListResponse>({ path: "/api/v1/runs", signal })).items;
  }

  get(runId: string, signal?: AbortSignal): Promise<RunDto> {
    return this.api.request<RunDto>({
      path: `/api/v1/runs/${encodeURIComponent(runId)}`,
      signal,
    });
  }

  async timeline(
    runId: string,
    signal?: AbortSignal,
  ): Promise<readonly TimelineEventDto[]> {
    return (
      await this.api.request<TimelineResponse>({
        path: `/api/v1/runs/${encodeURIComponent(runId)}/timeline`,
        signal,
      })
    ).items;
  }
}
