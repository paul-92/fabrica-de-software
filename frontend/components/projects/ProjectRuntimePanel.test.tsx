// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

afterEach(cleanup);
const ready = { runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready" as const, version: "1", message: "Ready", authentication_command: null };
const result = { output: "Project structure", runtime_id: "codex", model_id: "model", usage: { input_units: 4, output_units: 2, total_units: 6, cost: null }, metadata: {}, execution_mode: "read_only" as const, changes: [] };
const props = { projectId: "p-1", projectName: "Pilot", workspacePath: "C:/pilot" };
function service(overrides: Partial<ProjectRuntimeWorkspaceService> = {}): ProjectRuntimeWorkspaceService {
  return { status: vi.fn().mockResolvedValue(ready), execute: vi.fn().mockResolvedValue(result), ...overrides };
}

describe("ProjectRuntimePanel", () => {
  it("shows not ready with settings link and read-only indicator", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ status: vi.fn().mockResolvedValue({ ...ready, ready: false, authenticated: false, state: "not_authenticated" }) })} />);
    expect(await screen.findByText("Not connected")).toBeTruthy();
    expect(screen.getByText("Read-only session")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Configure AI Runtime" }).getAttribute("href")).toBe("/settings/ai");
  });

  it("validates, submits once and renders real result and usage", async () => {
    const api = service();
    render(<ProjectRuntimePanel {...props} service={api} />);
    await screen.findByText("Ready");
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Instruction is required");
    fireEvent.change(screen.getByLabelText("Task"), { target: { value: " Inspect " } });
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(api.execute).toHaveBeenCalledWith("p-1", "Inspect", "read_only");
    expect(screen.getByText("6")).toBeTruthy();
  });

  it("preserves input after failure and allows retry", async () => {
    const execute = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(result);
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("Ready");
    fireEvent.change(screen.getByLabelText("Task"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByLabelText("Task") as HTMLTextAreaElement).value).toBe("Inspect");
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(execute).toHaveBeenCalledTimes(2);
  });

  it("requires explicit confirmation before workspace write", async () => {
    const writeResult = { ...result, execution_mode: "workspace_write" as const, changes: [
      { path: "src/new.ts", change_type: "created" as const, size_before: null, size_after: 12 },
      { path: "src/changed.ts", change_type: "modified" as const, size_before: 4, size_after: 8 },
      { path: "src/old.ts", change_type: "deleted" as const, size_before: 5, size_after: null },
    ] };
    const execute = vi.fn().mockResolvedValue(writeResult);
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("Ready");
    fireEvent.click(screen.getByLabelText("Allow workspace changes"));
    fireEvent.change(screen.getByLabelText("Task"), { target: { value: " Write safely " } });
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    expect(execute).not.toHaveBeenCalled();
    const confirmation = await screen.findByRole("alertdialog");
    expect(confirmation.textContent).toContain("Pilot");
    expect(confirmation.textContent).toContain("C:/pilot");
    expect(confirmation.textContent).toContain("workspace_write");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(execute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run with Codex" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirm and run" }));
    expect(await screen.findByText("src/new.ts")).toBeTruthy();
    expect(screen.getByText("src/changed.ts")).toBeTruthy();
    expect(screen.getByText("src/old.ts")).toBeTruthy();
    expect(screen.getByText("workspace_write")).toBeTruthy();
    expect(execute).toHaveBeenCalledOnce();
    expect(execute).toHaveBeenCalledWith("p-1", "Write safely", "workspace_write");
  });
});
