import { ApiClient } from "../api/client";
import type { AIRuntimeStatusDto } from "../api/dtos";

type AIRuntimeListDto = Readonly<{ items: readonly AIRuntimeStatusDto[] }>;

export class AIRuntimesClient {
  constructor(private readonly api: ApiClient) {}
  list(): Promise<AIRuntimeListDto> {
    return this.api.request({ path: "/api/v1/ai-runtimes" });
  }
  status(runtimeId: string): Promise<AIRuntimeStatusDto> {
    return this.api.request({
      path: `/api/v1/ai-runtimes/${encodeURIComponent(runtimeId)}/status`,
    });
  }
}
