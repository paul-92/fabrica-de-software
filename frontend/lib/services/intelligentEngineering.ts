import { ApiClient } from "../api/client";
import type {
  IntelligentEngineeringRequestDto,
  IntelligentEngineeringResponseDto,
} from "../api/dtos";

const EXECUTE_PATH = "/api/v1/intelligent-engineering/execute";

export class IntelligentEngineeringClient {
  constructor(private readonly api: ApiClient) {}

  execute(
    request: IntelligentEngineeringRequestDto,
    signal?: AbortSignal,
  ): Promise<IntelligentEngineeringResponseDto> {
    return this.api.request<IntelligentEngineeringResponseDto>({
      path: EXECUTE_PATH,
      method: "POST",
      body: request,
      signal,
    });
  }
}
