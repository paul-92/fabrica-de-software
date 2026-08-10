// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectsWorkspaceService } from "../../lib/services/projectsWorkspace";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ProjectsWorkspace } from "./ProjectsWorkspace";

afterEach(cleanup);
const project = { project_id: "p-1", name: "Project", workspace_path: "C:/work", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
function service(overrides: Partial<ProjectsWorkspaceService> = {}): ProjectsWorkspaceService {
  return { list: vi.fn().mockResolvedValue([]), create: vi.fn().mockResolvedValue(project), get: vi.fn().mockResolvedValue(project), ...overrides };
}
function runtimeService(): ProjectRuntimeWorkspaceService {
  return {
    status: vi.fn().mockResolvedValue({ runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready", version: "1", message: "Ready", authentication_command: null }),
    execute: vi.fn(),
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn(),
    listExecutions: vi.fn().mockResolvedValue([]),
    getExecution: vi.fn(),
  };
}

describe("ProjectsWorkspace", () => {
  it("shows loading and empty states", async () => {
    const view = render(<ProjectsWorkspace service={service({ list: () => new Promise(() => undefined) })} runtimeService={runtimeService()} />);
    expect(screen.getByRole("status").textContent).toContain("Loading projects");
    view.unmount();
    render(<ProjectsWorkspace service={service()} runtimeService={runtimeService()} />);
    expect(await screen.findByText("No projects yet")).toBeTruthy();
  });

  it("shows list error and retries", async () => {
    const list = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]);
    render(<ProjectsWorkspace service={service({ list })} runtimeService={runtimeService()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No projects yet")).toBeTruthy();
  });

  it("validates and creates a project that appears in the list", async () => {
    const api = service();
    const runtime = runtimeService();
    render(<ProjectsWorkspace service={api} runtimeService={runtime} />);
    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: " Project " } });
    fireEvent.change(screen.getByLabelText("Workspace path"), { target: { value: " C:/work " } });
    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    expect((await screen.findAllByText("p-1")).length).toBe(2);
    expect(await screen.findByText("No sessions yet.")).toBeTruthy();
    expect(api.create).toHaveBeenCalledWith({ name: "Project", workspace_path: "C:/work" });
    expect(runtime.status).toHaveBeenCalledOnce();
    expect(runtime.listSessions).toHaveBeenCalledWith("p-1");
  });

  it("preserves input after creation error", async () => {
    render(<ProjectsWorkspace service={service({ create: vi.fn().mockRejectedValue(new Error()) })} runtimeService={runtimeService()} />);
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Project" } });
    fireEvent.change(screen.getByLabelText("Workspace path"), { target: { value: "C:/bad" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    expect(await screen.findByText(/could not be created/)).toBeTruthy();
    expect((screen.getByLabelText("Project name") as HTMLInputElement).value).toBe("Project");
  });
});
