export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type HttpRequest = Readonly<{
  url: string;
  method: HttpMethod;
  headers?: Readonly<Record<string, string>>;
  body?: unknown;
  signal?: AbortSignal;
}>;

export type HttpResponse = Readonly<{
  status: number;
  ok: boolean;
  body: unknown;
}>;

export interface HttpTransport {
  send(request: HttpRequest): Promise<HttpResponse>;
}

export class HttpTimeoutError extends Error {
  constructor(
    public readonly timeoutMs: number,
    cause: unknown,
  ) {
    super(`HTTP request timed out after ${timeoutMs} ms.`, { cause });
    this.name = "HttpTimeoutError";
  }
}

export class FetchHttpTransport implements HttpTransport {
  constructor(private readonly timeoutMs = 10_000) {
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
      throw new RangeError("HTTP timeout must be a positive finite number.");
    }
  }

  async send(request: HttpRequest): Promise<HttpResponse> {
    const controller = new AbortController();
    let timedOut = false;
    const forwardAbort = () => controller.abort(request.signal?.reason);
    if (request.signal?.aborted) forwardAbort();
    else request.signal?.addEventListener("abort", forwardAbort, { once: true });
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.timeoutMs);

    try {
      const response = await fetch(request.url, {
        method: request.method,
        headers: {
          Accept: "application/json",
          ...(request.body === undefined ? {} : { "Content-Type": "application/json" }),
          ...request.headers,
        },
        body: request.body === undefined ? undefined : JSON.stringify(request.body),
        signal: controller.signal,
      });
      const contentType = response.headers.get("content-type") ?? "";
      const body =
        response.status === 204
          ? undefined
          : contentType.includes("application/json")
            ? await response.json()
            : await response.text();

      return { status: response.status, ok: response.ok, body };
    } catch (error) {
      if (timedOut) throw new HttpTimeoutError(this.timeoutMs, error);
      throw error;
    } finally {
      clearTimeout(timeout);
      request.signal?.removeEventListener("abort", forwardAbort);
    }
  }
}
