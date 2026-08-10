// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { MetricsSummaryDto, RunDto } from "../../lib/api/dtos";
import type { QualityData, QualityLoader } from "../../lib/services/quality";
import { QualityWorkspace } from "./QualityWorkspace";

afterEach(cleanup);

const summary: MetricsSummaryDto = {
  total_runs: 4, successful_runs: 3, failed_runs: 1, running_runs: 0,
  pending_runs: 0, cancelled_runs: 0, unknown_status_runs: 0,
  eligible_runs: 4, success_rate: 75, failure_rate: 25,
  duration: { count: 4, ignored_count: 0, minimum_seconds: 1, maximum_seconds: 10, average_seconds: 5, median_seconds: 4 },
};

const recentRun: RunDto = {
  id: "run-4", status: "failed", started_at: "2026-08-10T10:00:00Z", finished_at: "2026-08-10T10:00:05Z",
  project_id: "project-1", workflow_id: "workflow-1", stage_id: "validation", provider_name: "codex",
  summary: null, error: { type: "ValidationError", message: "Validação reprovada", details: {} }, metadata: {},
};

const data: QualityData = {
  summary,
  statuses: [{ status: "succeeded", count: 3 }, { status: "failed", count: 1 }],
  providers: [{ provider_name: "codex", total_runs: 4, successful_runs: 3, failed_runs: 1, running_runs: 0, unknown_status_runs: 0, eligible_runs: 4, success_rate: 75, failure_rate: 25, duration: summary.duration }],
  recentRuns: [recentRun],
};

const loader = (load: QualityLoader["load"]): QualityLoader => ({ load });

describe("QualityWorkspace", () => {
  it("announces loading and renders operational quality data", async () => {
    let resolve!: (value: QualityData) => void;
    const load = vi.fn(() => new Promise<QualityData>((done) => { resolve = done; }));
    render(<QualityWorkspace loader={loader(load)} />);
    expect(screen.getByRole("status").textContent).toContain("Carregando indicadores de qualidade");

    await act(async () => { resolve(data); });

    expect(await screen.findByRole("heading", { name: "Distribuição por status" })).toBeTruthy();
    expect(screen.getAllByText("75%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("25%").length).toBeGreaterThan(0);
    expect(screen.getByText("Concluído")).toBeTruthy();
    expect(screen.getAllByText("codex").length).toBeGreaterThan(0);
    expect(screen.getByText("run-4")).toBeTruthy();
    expect(screen.getByText("Validação reprovada")).toBeTruthy();
  });

  it("shows the empty state when no public quality data exists", async () => {
    const empty: QualityData = {
      summary: { ...summary, total_runs: 0, successful_runs: 0, failed_runs: 0, eligible_runs: 0, success_rate: 0, failure_rate: 0 },
      statuses: [], providers: [], recentRuns: [],
    };
    render(<QualityWorkspace loader={loader(vi.fn().mockResolvedValue(empty))} />);
    expect(await screen.findByText("Nenhum dado de qualidade ainda")).toBeTruthy();
  });

  it("shows a safe error and retries", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("internal detail")).mockResolvedValueOnce(data);
    render(<QualityWorkspace loader={loader(load)} />);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Qualidade indisponível");
    expect(document.body.textContent).not.toContain("internal detail");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("run-4")).toBeTruthy();
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });
});
