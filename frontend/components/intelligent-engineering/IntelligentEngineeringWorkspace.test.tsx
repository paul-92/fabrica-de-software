// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { IntelligentEngineeringRequestDto, IntelligentEngineeringResponseDto } from "../../lib/api/dtos";
import { IntelligentEngineeringWorkspace } from "./IntelligentEngineeringWorkspace";

afterEach(cleanup);

function response(): IntelligentEngineeringResponseDto {
  const analysis = { summary: "Broken behavior" };
  const plan = { analysis, changes: [{ path: "app.py", content: "fixed", overwrite: true, reason: "Correct behavior" }], test_paths: ["tests/unit"] };
  return {
    planning_request: { goal: "Repair application", context: { objective: "Restore behavior" } },
    planning_result: {
      plan: { plan_id: "plan-1", goal: "Repair application", steps: [{ step_id: "step-1", description: "Apply controlled repair", required_capability: "repair", tool_id: null, agent_id: null, dependencies: [], priority: 1, status: "pending", estimated_cost: 1, estimated_duration_seconds: 2, metadata: {} }], estimated_cost: 1, estimated_duration_seconds: 2, created_at: "2026-08-07T10:00:00Z", metadata: {} },
      warnings: ["Review required"], validation_messages: [], statistics: { total_steps: 1, dependency_count: 0, maximum_depth: 1, estimated_cost: 1, estimated_duration_seconds: 2, memory_entries_considered: 0 },
    },
    engineering_result: {
      proposal: { summary: "Repair proposal", reasoning: "Observed failure", candidate_files: ["app.py"], suggested_actions: ["Review change"], confidence: 0.8 },
      plan,
      repair_result: { status: "succeeded", attempts: [], final_analysis: null, messages: ["Tests passed"] },
      reflection: { summary: "Repair succeeded", outcome: "succeeded", lessons: ["Validate behavior"], recommended_actions: ["Monitor"], should_retry: false, confidence: 0.9 },
    },
  };
}

function fillForm() {
  fireEvent.change(screen.getByLabelText(/Engineering goal/), { target: { value: "Repair application" } });
  fireEvent.change(screen.getByLabelText(/Planning objective/), { target: { value: "Restore behavior" } });
  fireEvent.change(screen.getByLabelText(/Failure analysis summary/), { target: { value: "Broken behavior" } });
  fireEvent.change(screen.getByLabelText(/Replacement target path/), { target: { value: "  app.py  " } });
  fireEvent.change(screen.getByLabelText(/Explicit replacement content/), { target: { value: "fixed" } });
  fireEvent.change(screen.getByLabelText(/Test paths/), { target: { value: "tests/unit, tests/integration" } });
}

describe("IntelligentEngineeringWorkspace", () => {
  it("starts idle and validates required fields", async () => {
    const executor = { execute: vi.fn() };
    render(<IntelligentEngineeringWorkspace executor={executor} />);
    expect(screen.getByRole("heading", { name: "Intelligent Engineering" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Run Intelligent Engineering" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Complete all required fields");
    expect(executor.execute).not.toHaveBeenCalled();
  });

  it("submits the real DTO while preserving explicit values", async () => {
    const executor = { execute: vi.fn().mockResolvedValue(response()) };
    render(<IntelligentEngineeringWorkspace executor={executor} />); fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Run Intelligent Engineering" }));
    await waitFor(() => expect(executor.execute).toHaveBeenCalledOnce());
    expect(executor.execute.mock.calls[0][0]).toEqual({
      planning_request: { goal: "Repair application", context: { objective: "Restore behavior" } },
      knowledge_context: { learned_entries: [], knowledge_count: 0 },
      engineering_request: {
        analysis: {
          summary: "Broken behavior",
          affected_paths: ["app.py"],
        },
        replacement_contents: { "app.py": "fixed" },
        test_paths: ["tests/unit", "tests/integration"],
      },
    } satisfies IntelligentEngineeringRequestDto);
    const request = executor.execute.mock.calls[0][0];
    expect(request.engineering_request.analysis.affected_paths).toEqual([
      "app.py",
    ]);
    expect(Object.keys(request.engineering_request.replacement_contents)).toEqual([
      "app.py",
    ]);
  });

  it("shows submitting and prevents duplicate submissions", async () => {
    let resolve!: (value: IntelligentEngineeringResponseDto) => void;
    const execute = vi.fn(() => new Promise<IntelligentEngineeringResponseDto>((done) => { resolve = done; }));
    render(<IntelligentEngineeringWorkspace executor={{ execute }} />); fillForm();
    const form = screen.getByRole("button", { name: "Run Intelligent Engineering" }).closest("form")!;
    fireEvent.submit(form); fireEvent.submit(form);
    expect((await screen.findByRole("button", { name: "Running…" }) as HTMLButtonElement).disabled).toBe(true);
    expect(execute).toHaveBeenCalledOnce();
    resolve(response());
    expect(await screen.findByText("Execution result")).toBeTruthy();
  });

  it("renders real planning, repair and reflection response fields", async () => {
    render(<IntelligentEngineeringWorkspace executor={{ execute: vi.fn().mockResolvedValue(response()) }} />); fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Run Intelligent Engineering" }));
    expect(await screen.findByText("Apply controlled repair")).toBeTruthy();
    expect(screen.getByText("Repair proposal")).toBeTruthy();
    expect(screen.getByText("Tests passed")).toBeTruthy();
    expect(screen.getByText("Repair succeeded")).toBeTruthy();
    expect(screen.getByText("Retry recommended: No")).toBeTruthy();
  });

  it("shows an error, preserves input and permits a new submission", async () => {
    const execute = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(response());
    render(<IntelligentEngineeringWorkspace executor={{ execute }} />); fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Run Intelligent Engineering" }));
    expect((await screen.findByRole("alert")).textContent).toContain("could not be completed");
    expect((screen.getByLabelText(/Engineering goal/) as HTMLTextAreaElement).value).toBe("Repair application");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Execution result")).toBeTruthy();
    expect(execute).toHaveBeenCalledTimes(2);
  });
});
