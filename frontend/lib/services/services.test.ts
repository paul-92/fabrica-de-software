import { describe, expect, it } from "vitest";

import { ApiClient } from "../api/client";
import type { IntelligentEngineeringRequestDto } from "../api/dtos";
import type { HttpRequest, HttpResponse, HttpTransport } from "../api/http";
import { IntelligentEngineeringClient } from "./intelligentEngineering";
import { MetricsClient } from "./metrics";
import { RunsClient } from "./runs";
import { ProjectsClient } from "./projects";

class RecordingTransport implements HttpTransport {
  requests: HttpRequest[] = [];
  responses: HttpResponse[] = [];

  async send(request: HttpRequest): Promise<HttpResponse> {
    this.requests.push(request);
    return this.responses.shift() ?? { status: 200, ok: true, body: {} };
  }
}

function setup() {
  const transport = new RecordingTransport();
  const api = new ApiClient({ baseUrl: "https://example.test" }, transport);
  return { transport, api };
}

describe("specialized API clients", () => {
  it("executes Intelligent Engineering through its public endpoint", async () => {
    const { transport, api } = setup();
    const request: IntelligentEngineeringRequestDto = {
      planning_request: {
        goal: "Plan",
        context: { objective: "Repair" },
      },
      knowledge_context: { knowledge_count: 0 },
      engineering_request: {
        analysis: { summary: "Failure" },
        replacement_contents: { "app.py": "replacement" },
      },
    };
    transport.responses.push({ status: 200, ok: true, body: { result: true } });

    await new IntelligentEngineeringClient(api).execute(request);

    expect(transport.requests[0]).toMatchObject({
      url: "https://example.test/api/v1/intelligent-engineering/execute",
      method: "POST",
      body: request,
    });
  });

  it("provides run details, lists and timeline through encoded paths", async () => {
    const { transport, api } = setup();
    transport.responses.push(
      { status: 200, ok: true, body: { items: [] } },
      { status: 200, ok: true, body: { id: "run/one" } },
      { status: 200, ok: true, body: { items: [] } },
    );
    const runs = new RunsClient(api);

    await runs.list();
    await runs.get("run/one");
    await runs.timeline("run/one");

    expect(transport.requests.map(({ url }) => url)).toEqual([
      "https://example.test/api/v1/runs",
      "https://example.test/api/v1/runs/run%2Fone",
      "https://example.test/api/v1/runs/run%2Fone/timeline",
    ]);
  });

  it("encodes every special character in run ids before building paths", async () => {
    const { transport, api } = setup();
    transport.responses.push(
      { status: 200, ok: true, body: { id: "run/a ?#" } },
      { status: 200, ok: true, body: { items: [] } },
    );
    const runs = new RunsClient(api);

    await runs.get("run/a ?#");
    await runs.timeline("run/a ?#");

    expect(transport.requests.map(({ url }) => url)).toEqual([
      "https://example.test/api/v1/runs/run%2Fa%20%3F%23",
      "https://example.test/api/v1/runs/run%2Fa%20%3F%23/timeline",
    ]);
  });

  it("provides all public metrics resources", async () => {
    const { transport, api } = setup();
    transport.responses.push(
      { status: 200, ok: true, body: { total_runs: 0 } },
      { status: 200, ok: true, body: { items: [] } },
      { status: 200, ok: true, body: { items: [] } },
    );
    const metrics = new MetricsClient(api);

    await metrics.summary();
    await metrics.byStatus();
    await metrics.byProvider();

    expect(transport.requests.map(({ url }) => url)).toEqual([
      "https://example.test/api/v1/metrics/summary",
      "https://example.test/api/v1/metrics/status",
      "https://example.test/api/v1/metrics/providers",
    ]);
  });

  it("provides project create, list and encoded details", async () => {
    const { transport, api } = setup();
    transport.responses.push(
      { status: 201, ok: true, body: { project_id: "project/one" } },
      { status: 200, ok: true, body: { items: [] } },
      { status: 200, ok: true, body: { project_id: "project/one" } },
    );
    const projects = new ProjectsClient(api);
    const request = { name: "Project", workspace_path: "C:/work" };

    await projects.create(request);
    await projects.list();
    await projects.get("project/one");

    expect(transport.requests).toMatchObject([
      { url: "https://example.test/api/v1/projects", method: "POST", body: request },
      { url: "https://example.test/api/v1/projects", method: "GET" },
      { url: "https://example.test/api/v1/projects/project%2Fone", method: "GET" },
    ]);
  });
});
