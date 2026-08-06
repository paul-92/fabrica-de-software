import { afterEach, describe, expect, it, vi } from "vitest";

import { FetchHttpTransport, HttpTimeoutError } from "./http";

describe("FetchHttpTransport", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("serializes JSON requests and parses JSON responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await new FetchHttpTransport().send({
      url: "https://platform.example/api/v1/action",
      method: "POST",
      body: { goal: "test" },
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "https://platform.example/api/v1/action",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ goal: "test" }),
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(response).toEqual({ status: 200, ok: true, body: { ok: true } });
  });

  it("supports empty successful responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );

    await expect(
      new FetchHttpTransport().send({
        url: "https://platform.example/api/v1/action",
        method: "DELETE",
      }),
    ).resolves.toEqual({ status: 204, ok: true, body: undefined });
  });

  it("aborts and rejects a stalled request after the configured timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string | URL | Request, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
      ),
    );

    const request = new FetchHttpTransport(50).send({
      url: "https://platform.example/api/v1/runs",
      method: "GET",
    });
    const rejection = expect(request).rejects.toMatchObject({
      name: "HttpTimeoutError",
      timeoutMs: 50,
    } satisfies Partial<HttpTimeoutError>);
    await vi.advanceTimersByTimeAsync(50);

    await rejection;
  });
});
