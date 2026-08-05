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

export class FetchHttpTransport implements HttpTransport {
  async send(request: HttpRequest): Promise<HttpResponse> {
    const response = await fetch(request.url, {
      method: request.method,
      headers: {
        Accept: "application/json",
        ...(request.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...request.headers,
      },
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
      signal: request.signal,
    });
    const contentType = response.headers.get("content-type") ?? "";
    const body =
      response.status === 204
        ? undefined
        : contentType.includes("application/json")
          ? await response.json()
          : await response.text();

    return { status: response.status, ok: response.ok, body };
  }
}
