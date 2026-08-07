// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

afterEach(cleanup);
const ready = { runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready" as const, version: "1", message: "Ready", authentication_command: null };
const result = { output: "Project structure", runtime_id: "codex", model_id: "model", usage: { input_units: 4, output_units: 2, total_units: 6, cost: null }, metadata: {} };
function service(overrides: Partial<ProjectRuntimeWorkspaceService> = {}): ProjectRuntimeWorkspaceService {
  return { status: vi.fn().mockResolvedValue(ready), execute: vi.fn().mockResolvedValue(result), ...overrides };
}

describe("ProjectRuntimePanel", () => {
  it("shows not ready with settings link and read-only indicator", async () => {
    render(<ProjectRuntimePanel projectId="p-1" service={service({ status: vi.fn().mockResolvedValue({ ...ready, ready: false, authenticated: false, state: "not_authenticated" }) })} />);
    expect(await screen.findByText("Not connected")).toBeTruthy();
    expect(screen.getByText("Read-only session")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Configure AI Runtime" }).getAttribute("href")).toBe("/settings/ai");
  });

  it("validates, submits once and renders real result and usage", async () => {
    const api = service();
    render(<ProjectRuntimePanel projectId="p-1" service={api} />);
    await screen.findByText("Ready");
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Instruction is required");
    fireEvent.change(screen.getByLabelText("Task"), { target: { value: " Inspect " } });
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(api.execute).toHaveBeenCalledWith("p-1", "Inspect");
    expect(screen.getByText("6")).toBeTruthy();
  });

  it("preserves input after failure and allows retry", async () => {
    const execute = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(result);
    render(<ProjectRuntimePanel projectId="p-1" service={service({ execute })} />);
    await screen.findByText("Ready");
    fireEvent.change(screen.getByLabelText("Task"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByLabelText("Task") as HTMLTextAreaElement).value).toBe("Inspect");
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(execute).toHaveBeenCalledTimes(2);
  });
});
