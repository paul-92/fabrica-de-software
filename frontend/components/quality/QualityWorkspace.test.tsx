// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { MetricsSummaryDto, RunDto } from "../../lib/api/dtos";
import type { SequentialQualityGateDto } from "../../lib/api/dtos";
import { ApiHttpError } from "../../lib/api/errors";
import type { QualityData, QualityLoader } from "../../lib/services/quality";
import type { SequentialQualityLoader } from "../../lib/services/sequentialQuality";
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
const sequentialLoader = (
  load: SequentialQualityLoader["load"],
): SequentialQualityLoader => ({ load });

const gates: readonly SequentialQualityGateDto[] = [
  {
    gate_id: "QG-APPROVED", execution_id: "exec-1", stage_id: "analysis",
    decision: "APPROVED", satisfied_criteria: ["Escopo aprovado"],
    unsatisfied_criteria: [], evaluated_at: "2026-08-11T12:00:00Z",
  },
  {
    gate_id: "QG-PENDING", execution_id: "exec-1", stage_id: "review",
    decision: "APPROVED_WITH_PENDING", satisfied_criteria: [],
    unsatisfied_criteria: ["Revisão final pendente"],
    evaluated_at: "2026-08-11T13:00:00Z",
  },
  {
    gate_id: "QG-BLOCKED", execution_id: "exec-1", stage_id: "release",
    decision: "BLOCKED", satisfied_criteria: [],
    unsatisfied_criteria: ["Aprovação ausente"],
    evaluated_at: "2026-08-11T14:00:00Z",
  },
];

function submitSequentialQuery() {
  fireEvent.change(screen.getByLabelText("Projeto sequencial"), {
    target: { value: " sample " },
  });
  fireEvent.change(screen.getByLabelText("Execução sequencial"), {
    target: { value: " exec-1 " },
  });
  fireEvent.click(screen.getByRole("button", { name: "Consultar Quality Gates" }));
}

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

  it("starts the sequential section idle and validates both identifiers", async () => {
    const loadSequential = vi.fn();
    render(<QualityWorkspace
      loader={loader(vi.fn().mockResolvedValue(data))}
      sequentialLoader={sequentialLoader(loadSequential)}
    />);
    expect(await screen.findByRole("heading", { name: "Quality Gates sequenciais" })).toBeTruthy();
    expect(screen.getByText("Informe os identificadores para iniciar a consulta.")).toBeTruthy();
    expect(screen.queryByRole("combobox")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Consultar Quality Gates" }));
    expect(screen.getByRole("alert").textContent).toContain("Informe o projeto sequencial e a execução");
    expect(loadSequential).not.toHaveBeenCalled();
  });

  it("announces sequential loading and renders every canonical field and decision", async () => {
    let resolve!: (items: readonly SequentialQualityGateDto[]) => void;
    const loadSequential = vi.fn(() => new Promise<readonly SequentialQualityGateDto[]>((done) => { resolve = done; }));
    render(<QualityWorkspace
      loader={loader(vi.fn().mockResolvedValue(data))}
      sequentialLoader={sequentialLoader(loadSequential)}
    />);
    submitSequentialQuery();
    expect(screen.getByText("Carregando Quality Gates sequenciais…").getAttribute("role")).toBe("status");
    await act(async () => { resolve(gates); });

    expect(loadSequential).toHaveBeenCalledWith("sample", "exec-1");
    for (const text of [
      "QG-APPROVED", "analysis", "exec-1", "Aprovado",
      "QG-PENDING", "review", "Aprovado com pendências",
      "QG-BLOCKED", "release", "Bloqueado", "Escopo aprovado",
      "Revisão final pendente", "Aprovação ausente",
    ]) expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/11 de ago\. de 2026/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("list").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Critérios atendidos").length).toBe(3);
    expect(screen.getAllByText("Critérios não atendidos").length).toBe(3);
    expect(screen.getAllByText("Nenhum critério atendido registrado.").length).toBe(2);
    expect(screen.getByText("Nenhum critério não atendido registrado.")).toBeTruthy();
  });

  it("shows the sequential empty state without hiding aggregate quality", async () => {
    render(<QualityWorkspace
      loader={loader(vi.fn().mockResolvedValue(data))}
      sequentialLoader={sequentialLoader(vi.fn().mockResolvedValue([]))}
    />);
    submitSequentialQuery();
    expect(await screen.findByText("Nenhum Quality Gate registrado para esta execução.")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Distribuição por status" })).toBeTruthy();
  });

  it.each([
    [404, "Não foi possível localizar os resultados desta execução sequencial."],
    [500, "Não foi possível consultar os Quality Gates no momento."],
  ])("shows a safe sequential error for HTTP %s and preserves inputs", async (status, message) => {
    const loadSequential = vi.fn().mockRejectedValue(
      new ApiHttpError(status, "SAFE", "server message", { secret: "C:\\private" }),
    );
    render(<QualityWorkspace
      loader={loader(vi.fn().mockResolvedValue(data))}
      sequentialLoader={sequentialLoader(loadSequential)}
    />);
    submitSequentialQuery();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(message);
    expect(document.body.textContent).not.toContain("private");
    expect((screen.getByLabelText("Projeto sequencial") as HTMLInputElement).value).toBe(" sample ");
    expect((screen.getByLabelText("Execução sequencial") as HTMLInputElement).value).toBe(" exec-1 ");
  });

  it("retries only the sequential query without reloading aggregate data", async () => {
    const aggregate = vi.fn().mockResolvedValue(data);
    const sequential = vi.fn()
      .mockRejectedValueOnce(new ApiHttpError(500, "ERROR", "safe"))
      .mockResolvedValueOnce(gates);
    render(<QualityWorkspace
      loader={loader(aggregate)}
      sequentialLoader={sequentialLoader(sequential)}
    />);
    submitSequentialQuery();
    await screen.findByText("Não foi possível consultar os Quality Gates no momento.");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("QG-APPROVED")).toBeTruthy();
    expect(sequential).toHaveBeenCalledTimes(2);
    expect(aggregate).toHaveBeenCalledOnce();
  });

  it("does not render unknown backend fields or unsupported semantics", async () => {
    const raw = [{
      ...gates[0], project_id: "public-project", run_id: "run-internal",
      path: "C:\\secret", evidence: "raw", health: "healthy",
      severity: "critical", recommendation: "invented",
    }] as unknown as readonly SequentialQualityGateDto[];
    render(<QualityWorkspace
      loader={loader(vi.fn().mockResolvedValue(data))}
      sequentialLoader={sequentialLoader(vi.fn().mockResolvedValue(raw))}
    />);
    submitSequentialQuery();
    await screen.findByText("QG-APPROVED");
    const sequentialSection = screen.getByRole("heading", {
      name: "Quality Gates sequenciais",
    }).closest("article");
    expect(sequentialSection).toBeTruthy();
    for (const forbidden of [
      "public-project", "run-internal", "C:\\secret", "raw", "healthy",
      "critical", "invented", "Evidências", "Recomendação", "Severidade",
    ]) expect(sequentialSection?.textContent).not.toContain(forbidden);
  });
});
