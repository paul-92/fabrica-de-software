import type { ApiConfig } from "./config";
import { ApiError, ApiHttpError, ApiNetworkError, ApiResponseError, ApiTimeoutError } from "./errors";
import { HttpTimeoutError, type HttpMethod, type HttpTransport } from "./http";

type ApiRequest = Readonly<{
  path: string;
  method?: HttpMethod;
  body?: unknown;
  signal?: AbortSignal;
}>;

type ErrorEnvelope = {
  error?: { code?: string; message?: string };
};

export class ApiClient {
  constructor(
    private readonly config: ApiConfig,
    private readonly transport: HttpTransport,
  ) {}

  async request<T>({
    path,
    method = "GET",
    body,
    signal,
  }: ApiRequest): Promise<T> {
    try {
      const response = await this.transport.send({
        url: `${this.config.baseUrl}/${path.replace(/^\/+/, "")}`,
        method,
        body,
        signal,
      });
      if (!response.ok) {
        const envelope = this.errorEnvelope(response.body);
        throw new ApiHttpError(
          response.status,
          envelope?.error?.code ?? "HTTP_ERROR",
          envelope?.error?.message ?? `HTTP request failed with status ${response.status}.`,
          response.body,
        );
      }
      if (response.body === undefined) {
        throw new ApiResponseError("API response did not contain a body.");
      }
      return response.body as T;
    } catch (error) {
      if (error instanceof HttpTimeoutError) {
        throw new ApiTimeoutError(error.timeoutMs, error);
      }
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiNetworkError("Unable to communicate with the API.", error);
    }
  }

  private errorEnvelope(body: unknown): ErrorEnvelope | undefined {
    if (typeof body !== "object" || body === null) return undefined;
    const envelope = body as {
      error?: { code?: unknown; message?: unknown };
    };
    if (typeof envelope.error !== "object" || envelope.error === null) return undefined;
    return {
      error: {
        code: typeof envelope.error.code === "string" ? envelope.error.code : undefined,
        message:
          typeof envelope.error.message === "string" ? envelope.error.message : undefined,
      },
    };
  }
}
