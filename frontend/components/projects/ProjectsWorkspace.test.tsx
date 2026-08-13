// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectsWorkspaceService } from "../../lib/services/projectsWorkspace";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import type { ProjectWorkspaceService } from "../../lib/services/projectWorkspaceService";
import { ProjectsWorkspace } from "./ProjectsWorkspace";

afterEach(() => { cleanup(); window.history.replaceState(null, "", "/projects"); });
const project = { project_id: "p-1", name: "Project", workspace_path: "C:/work", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
function service(overrides: Partial<ProjectsWorkspaceService> = {}): ProjectsWorkspaceService {
  return { list: vi.fn().mockResolvedValue([]), create: vi.fn().mockResolvedValue(project), get: vi.fn().mockResolvedValue(project), ...overrides };
}
function runtimeService(): ProjectRuntimeWorkspaceService {
  return {
    status: vi.fn().mockResolvedValue({ runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready", version: "1", message: "Ready", authentication_command: null }),
    execute: vi.fn(),
    prepare: vi.fn(),
    approve: vi.fn(),
    cancel: vi.fn(),
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn(),
    listExecutions: vi.fn().mockResolvedValue([]),
    getExecution: vi.fn(),
    listMemory: vi.fn().mockResolvedValue([]),
    addMemory: vi.fn(),
  };
}
function workspaceService(): ProjectWorkspaceService { return { listDirectory: vi.fn().mockResolvedValue({ path: "", entries: [] }), readFile: vi.fn() }; }

describe("ProjectsWorkspace", () => {
  it("reads stable context IDs directly from the URL", async () => {
    window.history.replaceState(null, "", "/projects?project_id=p-1&session_id=s-1&execution_id=e-1");
    const execution = { execution_id: "e-1", session_id: "s-1", project_id: "p-1", runtime_id: "codex", instruction: "Open", execution_mode: "read_only" as const, status: "running" as const, output: null, model: null, usage: null, changes: [], error_code: null, context_entry_count: 0, context_truncated: false, context_char_count: 0, context_omitted_execution_count: 0, memory_entry_count: 0, memory_char_count: 0, memory_truncated: false, created_at: "2026-08-07T00:00:00Z", completed_at: null };
    const session = { session_id: "s-1", project_id: "p-1", title: "URL session", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
    const runtime = runtimeService();
    vi.mocked(runtime.listSessions).mockResolvedValue([session]);
    vi.mocked(runtime.getExecution).mockResolvedValue(execution);
    render(<ProjectsWorkspace service={service()} runtimeService={runtime} workspaceService={workspaceService()} />);
    expect(await screen.findByText("Fase persistida: Em execução")).toBeTruthy();
    expect(runtime.getExecution).toHaveBeenCalledWith("p-1", "e-1");
  });

  it("reconstructs project, session and execution from stable IDs after refresh", async () => {
    const execution = { execution_id: "e-1", session_id: "s-1", project_id: "p-1", runtime_id: "codex", instruction: "Ship", execution_mode: "workspace_write" as const, status: "succeeded" as const, output: "Done", model: "model", usage: null, changes: [], error_code: null, context_entry_count: 0, context_truncated: false, context_char_count: 0, context_omitted_execution_count: 0, memory_entry_count: 0, memory_char_count: 0, memory_truncated: false, created_at: "2026-08-07T00:00:00Z", completed_at: "2026-08-07T00:00:01Z" };
    const session = { session_id: "s-1", project_id: "p-1", title: "Stable session", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
    const runtime = runtimeService();
    vi.mocked(runtime.listSessions).mockResolvedValue([session]);
    vi.mocked(runtime.listExecutions).mockResolvedValue([execution]);
    vi.mocked(runtime.getExecution).mockResolvedValue(execution);
    const projects = service({ list: vi.fn().mockResolvedValue([project]) });
    const context = { projectId: "p-1", sessionId: "s-1", executionId: "e-1" };
    const first = render(<ProjectsWorkspace service={projects} runtimeService={runtime} workspaceService={workspaceService()} initialContext={context} />);
    expect(await screen.findByText("Done")).toBeTruthy();
    expect(screen.getByText("Fase persistida: Finalizada com sucesso")).toBeTruthy();
    expect(projects.get).toHaveBeenCalledWith("p-1");
    expect(runtime.getExecution).toHaveBeenCalledWith("p-1", "e-1");
    first.unmount();
    render(<ProjectsWorkspace service={projects} runtimeService={runtime} workspaceService={workspaceService()} initialContext={context} />);
    expect(await screen.findByText("Done")).toBeTruthy();
    expect(vi.mocked(runtime.getExecution).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("reports and retries an unknown project from the URL", async () => {
    const get = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(project);
    render(<ProjectsWorkspace service={service({ get })} runtimeService={runtimeService()} workspaceService={workspaceService()} initialContext={{ projectId: "missing" }} />);
    expect(await screen.findByText("Contexto do projeto não encontrado")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Detalhes do projeto")).toBeTruthy();
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("shows loading and empty states", async () => {
    const view = render(<ProjectsWorkspace service={service({ list: () => new Promise(() => undefined) })} runtimeService={runtimeService()} />);
    expect(screen.getByRole("status").textContent).toContain("Carregando projetos");
    view.unmount();
    render(<ProjectsWorkspace service={service()} runtimeService={runtimeService()} />);
    expect(await screen.findByText("Nenhum projeto ainda")).toBeTruthy();
  });

  it("shows list error and retries", async () => {
    const list = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]);
    render(<ProjectsWorkspace service={service({ list })} runtimeService={runtimeService()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhum projeto ainda")).toBeTruthy();
  });

  it("opens a listed project and mounts its runtime panel", async () => {
    const runtime = runtimeService();
    render(<ProjectsWorkspace service={service({ list: vi.fn().mockResolvedValue([project]) })} runtimeService={runtime} workspaceService={workspaceService()} />);
    const projectButton = await screen.findByRole("button", { name: /Project.*C:\/work.*p-1/i });
    expect(screen.queryByText("Detalhes do projeto")).toBeNull();
    fireEvent.click(projectButton);
    expect(window.location.search).toBe("?project_id=p-1");
    expect(await screen.findByText("Detalhes do projeto")).toBeTruthy();
    expect(projectButton.getAttribute("aria-pressed")).toBe("true");
    expect(await screen.findByText("Nenhuma sessão ainda.")).toBeTruthy();
    expect(runtime.status).toHaveBeenCalledOnce();
    expect(runtime.listSessions).toHaveBeenCalledWith("p-1");
  });

  it("validates and creates a project that appears in the list", async () => {
    const api = service();
    const runtime = runtimeService();
    render(<ProjectsWorkspace service={api} runtimeService={runtime} workspaceService={workspaceService()} />);
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Nome do projeto"), { target: { value: " Project " } });
    fireEvent.change(screen.getByLabelText("Pasta do projeto"), { target: { value: " C:/work " } });
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto" }));
    expect((await screen.findAllByText("p-1")).length).toBe(2);
    expect(await screen.findByText("Nenhuma sessão ainda.")).toBeTruthy();
    expect(api.create).toHaveBeenCalledWith({ name: "Project", workspace_path: "C:/work" });
    expect(runtime.status).toHaveBeenCalledOnce();
    expect(runtime.listSessions).toHaveBeenCalledWith("p-1");
  });

  it("preserves input after creation error", async () => {
    const create = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(project);
    render(<ProjectsWorkspace service={service({ create })} runtimeService={runtimeService()} workspaceService={workspaceService()} />);
    fireEvent.change(screen.getByLabelText("Nome do projeto"), { target: { value: "Project" } });
    fireEvent.change(screen.getByLabelText("Pasta do projeto"), { target: { value: "C:/bad" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Não foi possível criar o projeto");
    expect((screen.getByLabelText("Nome do projeto") as HTMLInputElement).value).toBe("Project");
    expect((screen.getByLabelText("Pasta do projeto") as HTMLInputElement).value).toBe("C:/bad");
    fireEvent.change(screen.getByLabelText("Pasta do projeto"), { target: { value: "C:/work" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto" }));
    expect(await screen.findByText("Detalhes do projeto")).toBeTruthy();
    expect(create).toHaveBeenNthCalledWith(2, { name: "Project", workspace_path: "C:/work" });
  });
});
