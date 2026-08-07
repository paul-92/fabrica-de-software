// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

afterEach(cleanup);
const ready = { runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready" as const, version: "1", message: "Ready", authentication_command: null };
const result = { execution_id: "e-1", output: "Project structure", runtime_id: "codex", model_id: "model", usage: { input_units: 4, output_units: 2, total_units: 6, cost: null }, metadata: {}, execution_mode: "read_only" as const, changes: [] };
const session = { session_id: "s-1", project_id: "p-1", title: "Pilot session", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
const failedExecution = { execution_id: "e-failed", session_id: "s-1", project_id: "p-1", runtime_id: "codex", instruction: "Change file", execution_mode: "workspace_write" as const, status: "failed" as const, output: null, model: null, usage: { input_units: 10, output_units: 2, total_units: 12, cost: null }, changes: [{ path: "partial.txt", change_type: "created" as const, size_before: null, size_after: 2 }], error_code: "AI_RUNTIME_TIMEOUT", created_at: "2026-08-07T00:00:00Z", completed_at: "2026-08-07T00:00:01Z" };
const props = { projectId: "p-1", projectName: "Pilot", workspacePath: "C:/pilot" };
function service(overrides: Partial<ProjectRuntimeWorkspaceService> = {}): ProjectRuntimeWorkspaceService {
  return { status: vi.fn().mockResolvedValue(ready), execute: vi.fn().mockResolvedValue(result), listSessions: vi.fn().mockResolvedValue([session]), createSession: vi.fn().mockResolvedValue(session), listExecutions: vi.fn().mockResolvedValue([]), getExecution: vi.fn(), ...overrides };
}

describe("ProjectRuntimePanel", () => {
  it("loads sessions and retries a loading failure", async () => {
    const listSessions = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]);
    render(<ProjectRuntimePanel {...props} service={service({ listSessions })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry sessions" }));
    expect(await screen.findByText("No sessions yet.")).toBeTruthy();
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

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
    expect(api.execute).toHaveBeenCalledWith("p-1", "s-1", "Inspect", "read_only");
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
    expect((screen.getByLabelText("Allow workspace changes") as HTMLInputElement).checked).toBe(true);
    expect(execute).toHaveBeenCalledOnce();
    expect(execute).toHaveBeenCalledWith("p-1", "s-1", "Write safely", "workspace_write");
  });

  it("creates and selects a session while preserving input on error", async () => {
    const createSession = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce({ ...session, session_id: "s-2", title: "New work" });
    render(<ProjectRuntimePanel {...props} service={service({ listSessions: vi.fn().mockResolvedValue([]), createSession })} />);
    expect(await screen.findByText("No sessions yet.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Session title"), { target: { value: " New work " } });
    fireEvent.click(screen.getByRole("button", { name: "New session" }));
    expect(await screen.findByText(/could not be created/)).toBeTruthy();
    expect((screen.getByLabelText("Session title") as HTMLInputElement).value).toBe(" New work ");
    fireEvent.click(screen.getByRole("button", { name: "New session" }));
    expect(await screen.findByRole("button", { name: "New work" })).toBeTruthy();
    expect(createSession).toHaveBeenLastCalledWith("p-1", "New work");
  });

  it("shows persisted failed history, usage, changes and details", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions: vi.fn().mockResolvedValue([failedExecution]) })} />);
    const historyItem = await screen.findByRole("button", {
      name: /failed.*codex.*workspace_write.*change file.*1 files changed.*10 input tokens.*2 output tokens/i,
    });
    expect(historyItem.textContent).toContain("Change file");
    expect(historyItem.textContent).toContain("10 input tokens");
    expect(historyItem.textContent).toContain("2 output tokens");
    fireEvent.click(historyItem);
    expect(await screen.findByText("AI_RUNTIME_TIMEOUT")).toBeTruthy();
    expect(screen.getByText("partial.txt")).toBeTruthy();
  });
});
