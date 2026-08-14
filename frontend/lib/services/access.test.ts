import { describe, expect, it } from "vitest";
import { ApiClient } from "../api/client";
import type { HttpRequest, HttpResponse, HttpTransport } from "../api/http";
import { AccessClient } from "./access";

class RecordingTransport implements HttpTransport {
  requests: HttpRequest[] = [];
  async send(request: HttpRequest): Promise<HttpResponse> {
    this.requests.push(request);
    return { status: 201, ok: true, body: { user_id: "u-1", email: "member@example.test", status: "active" } };
  }
}

describe("AccessClient user administration", () => {
  it("uses the authenticated users endpoint and defaults role to member", async () => {
    const transport = new RecordingTransport();
    const access = new AccessClient(new ApiClient({ baseUrl: "https://beta.example.test" }, transport));
    await access.invite("member@example.test", "temporary-password");
    expect(transport.requests).toEqual([{
      url: "https://beta.example.test/api/v1/access/users",
      method: "POST",
      body: { email: "member@example.test", password: "temporary-password", role: "member" },
      signal: undefined,
    }]);
  });
});
