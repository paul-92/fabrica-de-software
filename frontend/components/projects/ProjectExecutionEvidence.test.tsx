// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ProjectEngineeringEvidenceDto } from "../../lib/api/dtos";
import { ProjectExecutionEvidence } from "./ProjectExecutionEvidence";

afterEach(cleanup);

const validation = (sequence: number, validator: string, status: "passed" | "failed", output: string) => ({
  execution_id: "e-1", sequence, validator, command: validator === "pytest" ? ["python", "-m", "pytest"] : ["npm", "run", validator], exit_code: status === "passed" ? 0 : 1, status, output, completed_at: `2026-08-12T00:00:0${sequence}Z`,
});

function view(evidence: ProjectEngineeringEvidenceDto) {
  return render(<ProjectExecutionEvidence evidence={{ execution_id: "e-1", status: "succeeded", ...evidence }} changes={[]} output="Technical result" />);
}

describe("ProjectExecutionEvidence quality experience", () => {
  it("summarizes and separates canonical tests from checks with bounded details", () => {
    view({ validations: [
      validation(1, "pytest", "passed", "142 passed"),
      validation(2, "vitest", "failed", "2 failed"),
      validation(3, "compileall", "passed", "compile ok"),
      validation(4, "typecheck", "passed", "types ok"),
      validation(5, "eslint", "passed", "lint ok"),
      validation(6, "next_build", "passed", "build ok"),
    ] });
    const summary = screen.getByLabelText("Resumo de qualidade");
    expect(within(summary).getByText("Validações").parentElement?.textContent).toContain("6");
    expect(within(summary).getByText("PASS").parentElement?.textContent).toContain("5");
    expect(within(summary).getByText("FAIL").parentElement?.textContent).toContain("1");
    const tests = screen.getByRole("region", { name: "Testes" });
    expect(within(tests).getByText("Testes Python")).toBeTruthy();
    expect(within(tests).getByText("Testes Vitest")).toBeTruthy();
    expect(within(tests).getByText("pytest")).toBeTruthy();
    expect(within(tests).getByText("vitest")).toBeTruthy();
    expect(within(tests).getByText("142 passed")).toBeTruthy();
    expect(within(tests).getByText("2 failed")).toBeTruthy();
    const checks = screen.getByRole("region", { name: "Checks" });
    for (const id of ["compileall", "typecheck", "eslint", "next_build"]) expect(within(checks).getByText(id)).toBeTruthy();
    expect(screen.getAllByText("Ver comando e output")).toHaveLength(6);
    expect(screen.getByText("python -m pytest")).toBeTruthy();
  });

  it("shows only evidence-backed repair and revalidation transitions with approved gate", () => {
    view({
      validations: [validation(1, "pytest", "failed", "failed first"), validation(2, "pytest", "passed", "passed after repair")],
      repair: { execution_id: "e-1", outcome: "succeeded", attempt_count: 1 },
      quality_gate: { gate_id: "g-1", execution_id: "e-1", stage_id: "validation", decision: "APPROVED", satisfied_criteria: ["pytest passed"], unsatisfied_criteria: [], evaluated_at: "2026-08-12T00:00:03Z" },
    });
    expect(screen.getByText((_, element) => element?.tagName === "LI" && element.textContent === "pytest: FAIL → repair → PASS")).toBeTruthy();
    expect(screen.getByText("APPROVED")).toBeTruthy();
    expect(screen.getByText("pytest passed")).toBeTruthy();
    expect(screen.getByText("Nenhum critério não atendido.")).toBeTruthy();
  });

  it("shows exhausted repair and blocked gate without inventing a revalidation link", () => {
    view({
      validations: [validation(1, "pytest", "failed", "still failing")],
      repair: { execution_id: "e-1", outcome: "exhausted", attempt_count: 2 },
      quality_gate: { gate_id: "g-1", execution_id: "e-1", stage_id: "validation", decision: "BLOCKED", satisfied_criteria: [], unsatisfied_criteria: ["pytest must pass"], evaluated_at: "2026-08-12T00:00:03Z" },
    });
    expect(screen.getByText("Não há vínculo individual de revalidation registrado nas evidências.")).toBeTruthy();
    expect(screen.getByText("BLOCKED")).toBeTruthy();
    expect(screen.getByText("pytest must pass")).toBeTruthy();
  });
});
