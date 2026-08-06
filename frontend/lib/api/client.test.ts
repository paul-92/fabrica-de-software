import { describe, expect, it } from "vitest";

import { ApiClient } from "./client";
import { ApiHttpError, ApiNetworkError, ApiResponseError, ApiTimeoutError } from "./errors";
import { HttpTimeoutError, type HttpRequest, type HttpResponse, type HttpTransport } from "./http";

class TransportFake implements HttpTransport {
  requests: HttpRequest[] = [];

  constructor(
    private readonly response?: HttpResponse,
    private readonly error?: unknown,
  ) {}

  async send(request: HttpRequest): Promise<HttpResponse> {
    this.requests.push(request);
    if (this.error) throw this.error;
    if (!this.response) throw new Error("Missing fake response");
    return this.response;
  }
}

describe("ApiClient", () => {
  it("joins configured base URL and relative resource path", async () => {
    const transport = new TransportFake({ status: 200, ok: true, body: { id: 1 } });
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      transport,
    );

    await expect(client.request<{ id: number }>({ path: "/runs" })).resolves.toEqual({
      id: 1,
    });
    expect(transport.requests[0]?.url).toBe(
      "https://platform.example/api/v1/runs",
    );
  });

  it("maps the API error envelope to a typed HTTP error", async () => {
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      new TransportFake({
        status: 422,
        ok: false,
        body: { error: { code: "INVALID", message: "Invalid request." } },
      }),
    );

    const error = await client.request({ path: "runs" }).catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiHttpError);
    expect(error).toMatchObject({ status: 422, code: "INVALID" });
  });

  it("uses a safe fallback for malformed HTTP errors", async () => {
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      new TransportFake({ status: 500, ok: false, body: "failure" }),
    );

    await expect(client.request({ path: "runs" })).rejects.toMatchObject({
      name: "ApiHttpError",
      code: "HTTP_ERROR",
      status: 500,
    });
  });

  it("maps transport failures to a typed network error", async () => {
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      new TransportFake(undefined, new TypeError("offline")),
    );

    await expect(client.request({ path: "runs" })).rejects.toBeInstanceOf(
      ApiNetworkError,
    );
  });

  it("preserves timeout semantics as a typed API error", async () => {
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      new TransportFake(undefined, new HttpTimeoutError(50, new Error("abort"))),
    );

    await expect(client.request({ path: "runs" })).rejects.toMatchObject({
      name: "ApiTimeoutError",
      timeoutMs: 50,
    } satisfies Partial<ApiTimeoutError>);
  });

  it("rejects successful responses without a body", async () => {
    const client = new ApiClient(
      { baseUrl: "https://platform.example/api/v1" },
      new TransportFake({ status: 204, ok: true, body: undefined }),
    );

    await expect(client.request({ path: "runs" })).rejects.toBeInstanceOf(
      ApiResponseError,
    );
  });
});
