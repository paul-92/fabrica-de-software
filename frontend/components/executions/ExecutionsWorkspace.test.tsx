// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RunDto, TimelineEventDto } from "../../lib/api/dtos";
import type { ExecutionsLoader } from "../../lib/services/executions";
import { ExecutionsWorkspace } from "./ExecutionsWorkspace";

afterEach(cleanup);

function run(id = "run-1", status = "completed"): RunDto {
  return { id, status, started_at: "2026-08-05T10:00:00Z", finished_at: "2026-08-05T10:01:30Z", project_id: "project-1", workflow_id: "workflow-1", stage_id: "analysis", provider_name: "provider-1", summary: "Completed summary", error: null, metadata: {} };
}

const event: TimelineEventDto = { id: "event-1", run_id: "run-1", timestamp: "2026-08-05T10:00:10Z", type: "stage.started", stage_id: "analysis", message: "Analysis started", metadata: { attempt: 1 } };

function loader(overrides: Partial<ExecutionsLoader> = {}): ExecutionsLoader {
  return {
    list: vi.fn().mockResolvedValue([run()]),
    get: vi.fn().mockResolvedValue(run()),
    timeline: vi.fn().mockResolvedValue([event]),
    ...overrides,
  };
}

describe("ExecutionsWorkspace", () => {
  it("shows list loading", () => {
    render(<ExecutionsWorkspace loader={loader({ list: () => new Promise(() => undefined) })} />);
    expect(screen.getByRole("status").textContent).toContain("Carregando execuções");
  });

  it("renders runs, duration and textual status", async () => {
    render(<ExecutionsWorkspace loader={loader()} />);
    expect(await screen.findByRole("button", { name: "Abrir execução run-1" })).toBeTruthy();
    expect(screen.getByText("Concluído")).toBeTruthy();
    expect(screen.getByText("1m 30s")).toBeTruthy();
    expect(screen.getByText("provider-1")).toBeTruthy();
  });

  it("shows the empty list state", async () => {
    render(<ExecutionsWorkspace loader={loader({ list: vi.fn().mockResolvedValue([]) })} />);
    expect(await screen.findByText("Nenhuma execução ainda")).toBeTruthy();
  });

  it("shows list errors and retries", async () => {
    const list = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([run()]);
    render(<ExecutionsWorkspace loader={loader({ list })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("button", { name: "Abrir execução run-1" })).toBeTruthy();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it("loads selected details and timeline with the correct id", async () => {
    const get = vi.fn().mockResolvedValue(run("run/a ?"));
    const timeline = vi.fn().mockResolvedValue([{ ...event, run_id: "run/a ?" }]);
    render(<ExecutionsWorkspace loader={loader({ list: vi.fn().mockResolvedValue([run("run/a ?")]), get, timeline })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abrir execução run/a ?" }));

    expect(await screen.findByText("Detalhes da execução")).toBeTruthy();
    expect(await screen.findByText("Analysis started")).toBeTruthy();
    expect(screen.getByText("Etapa: analysis")).toBeTruthy();
    expect(get).toHaveBeenCalledWith("run/a ?");
    expect(timeline).toHaveBeenCalledWith("run/a ?");
  });

  it("keeps the list visible when details fail", async () => {
    render(<ExecutionsWorkspace loader={loader({ get: vi.fn().mockRejectedValue(new Error("detail")) })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abrir execução run-1" }));
    expect(await screen.findByText("Detalhes indisponíveis")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Abrir execução run-1" })).toBeTruthy();
  });

  it("isolates timeline failure and retries it", async () => {
    const timeline = vi.fn().mockRejectedValueOnce(new Error("timeline")).mockResolvedValueOnce([event]);
    render(<ExecutionsWorkspace loader={loader({ timeline })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Abrir execução run-1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Analysis started")).toBeTruthy();
    await waitFor(() => expect(timeline).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("button", { name: "Abrir execução run-1" })).toBeTruthy();
  });
});
