// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectAIRuntimeExecutionDto, ProjectExecutionDto, SessionMemoryKind } from "../../lib/api/dtos";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ApiHttpError, ApiNetworkError, ApiTimeoutError } from "../../lib/api/errors";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

afterEach(cleanup);
const ready = { runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready" as const, version: "1", message: "Ready", authentication_command: null };
const result = { execution_id: "e-1", output: "Project structure", runtime_id: "codex", model_id: "model", usage: { input_units: 4, output_units: 2, total_units: 6, cost: null }, metadata: {}, execution_mode: "read_only" as const, changes: [], context_entry_count: 0, context_truncated: false, context_char_count: 79, context_omitted_execution_count: 0, memory_entry_count: 0, memory_char_count: 49, memory_truncated: false };
const session = { session_id: "s-1", project_id: "p-1", title: "Pilot session", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
const failedExecution = { execution_id: "e-failed", session_id: "s-1", project_id: "p-1", runtime_id: "codex", instruction: "Change file", execution_mode: "workspace_write" as const, status: "failed" as const, output: null, model: null, usage: { input_units: 10, output_units: 2, total_units: 12, cost: null }, changes: [{ path: "partial.txt", change_type: "created" as const, size_before: null, size_after: 2 }], error_code: "AI_RUNTIME_TIMEOUT", context_entry_count: 2, context_truncated: true, context_char_count: 17432, context_omitted_execution_count: 9, memory_entry_count: 1, memory_char_count: 120, memory_truncated: false, created_at: "2026-08-07T00:00:00Z", completed_at: "2026-08-07T00:00:01Z" };
const props = { projectId: "p-1", projectName: "Pilot", workspaceLabel: "workspace-1" };
function service(overrides: Partial<ProjectRuntimeWorkspaceService> = {}): ProjectRuntimeWorkspaceService {
  const preparation = { execution_id: "e-1", project_id: "p-1", session_id: "s-1", runtime_id: "codex", instruction: "Write safely", status: "pending" as const, analysis: { languages: ["TypeScript"], frameworks: ["Next.js"], package_managers: ["npm"], package_manifests: ["package.json"], modules: ["src"], entrypoints: [], dependencies: [], architecture: [], has_tests: true, file_count: 3, test_file_count: 1 }, operational_plan: { execution_id: "e-1", source: "ai", created_at: "2026-08-12T00:00:00Z", steps: [{ step_id: "execute", operation: "execute_workspace_task", description: "Implementar a tarefa.", dependencies: [], target_hints: ["src"], validation_hints: ["typecheck", "vitest"] }] }, dependency_plan: { project_id:"p-1",preparation_id:"e-1",items:[],created_at:"2026-08-12T00:00:00Z",version:1 }, created_at: "2026-08-12T00:00:00Z" };
  return { status: vi.fn().mockResolvedValue(ready), execute: vi.fn().mockResolvedValue(result), prepare: vi.fn().mockImplementation(async (_projectId, _sessionId, instruction) => ({ ...preparation, instruction })), approve: vi.fn().mockResolvedValue(result), cancel: vi.fn().mockResolvedValue(failedExecution), approveDependency:vi.fn(), rejectDependency:vi.fn(), listSessions: vi.fn().mockResolvedValue([session]), createSession: vi.fn().mockResolvedValue(session), listExecutions: vi.fn().mockResolvedValue([]), getExecution: vi.fn(), listMemory: vi.fn().mockResolvedValue([]), addMemory: vi.fn(), ...overrides };
}

describe("ProjectRuntimePanel", () => {
  it("shows a domain message for a dependency plan blocker", async () => {
    const defaults=service(); const prepared=await defaults.prepare("p-1","s-1","Write safely",{});
    render(<ProjectRuntimePanel {...props} service={service({prepare:vi.fn().mockResolvedValue({...prepared,status:"blocked",error_code:"dependency_plan_missing_source",blocker:"Dependências aguardando revisão",next_action:"Defina ou aprove a stack técnica na preparação da sprint."})})}/>);
    await screen.findByText(/Pronto/);
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"),{target:{value:"Write safely"}});
    fireEvent.click(screen.getByRole("button",{name:"Preparar plano"}));
    expect(await screen.findByText(/stack técnica ainda não possui uma fonte estruturada aprovada/)).toBeTruthy();
    expect(screen.getByText(/Defina ou aprove a stack técnica/)).toBeTruthy();
    expect(screen.queryByText(/comunicação foi interrompida antes/)).toBeNull();
  });

  it("shows the structured dependency plan and approves all through existing requests", async () => {
    const defaults=service();
    const prepared=await defaults.prepare("p-1","s-1","Write safely",{});
    const approveDependency=vi.fn().mockResolvedValue({});
    render(<ProjectRuntimePanel {...props} service={service({
      prepare:vi.fn().mockResolvedValue({...prepared,dependency_plan:{...prepared.dependency_plan,items:[{
        ecosystem:"node",package:"typescript",requested_version:"5.9.2",reason:"Approved foundation",
        source:"sprint_preparation",source_reference:"sprint-1",required:true,status:"pending",dependency_request_id:"dep-1",
      }]}}),approveDependency,
    })}/>);
    await screen.findByText(/Pronto/);
    expect(screen.getByText("Adicionar dependência manualmente (avançado)")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"),{target:{value:"Write safely"}});
    fireEvent.click(screen.getByRole("button",{name:"Preparar plano"}));
    expect(await screen.findByText("Dependências necessárias")).toBeTruthy();
    expect(screen.getByText("typescript")).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:"Aprovar todas"}));
    await act(async()=>{});
    expect(approveDependency).toHaveBeenCalledWith("p-1","dep-1");
  });

  it.each([
    ["pending", "Aguardando aprovação"],
    ["running", "Em execução"],
    ["succeeded", "Finalizada com sucesso"],
    ["failed", "Finalizada com falha"],
  ] as const)("reconstructs a %s execution from its persisted ID", async (status, phase) => {
    const persisted = { ...failedExecution, execution_id: `e-${status}`, status, error_code: status === "failed" ? "FAILED" : null, completed_at: status === "succeeded" || status === "failed" ? "2026-08-07T00:00:01Z" : null };
    const getExecution = vi.fn().mockResolvedValue(persisted);
    render(<ProjectRuntimePanel {...props} service={service({ getExecution, listExecutions: vi.fn().mockResolvedValue([persisted]) })} initialSessionId="s-1" initialExecutionId={`e-${status}`} />);
    expect(await screen.findByText(`Fase persistida: ${phase}`)).toBeTruthy();
    expect(getExecution).toHaveBeenCalledWith("p-1", `e-${status}`);
  });

  it("shows an unknown execution and retries reconstruction", async () => {
    const getExecution = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(failedExecution);
    render(<ProjectRuntimePanel {...props} service={service({ getExecution })} initialSessionId="s-1" initialExecutionId="e-failed" />);
    expect(await screen.findByText("A execução informada pela URL não foi encontrada.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Fase persistida: Finalizada com falha")).toBeTruthy();
    expect(getExecution).toHaveBeenCalledTimes(2);
  });

  it("loads sessions and retries a loading failure", async () => {
    const listSessions = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]);
    render(<ProjectRuntimePanel {...props} service={service({ listSessions })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma sessão ainda.")).toBeTruthy();
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

  it("shows not ready with settings link and read-only indicator", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ status: vi.fn().mockResolvedValue({ ...ready, ready: false, authenticated: false, state: "not_authenticated" }) })} />);
    expect(await screen.findByText("● Não conectado")).toBeTruthy();
    expect(screen.getByText("Sessão somente leitura")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Configurar assistente de IA" }).getAttribute("href")).toBe("/settings/ai");
  });

  it("renders the confirmed Codex ready contract and enables execution", async () => {
    const confirmedReady = { ...ready, version: "0.147.0-alpha.6.5", message: "Codex is ready." };
    render(<ProjectRuntimePanel {...props} service={service({ status: vi.fn().mockResolvedValue(confirmedReady) })} />);
    expect(await screen.findByText("● Pronto")).toBeTruthy();
    expect(screen.queryByText("● Não conectado")).toBeNull();
    expect((screen.getByLabelText("Tarefa") as HTMLTextAreaElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Executar com Codex" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it.each([
    ["not_installed", "● Não instalado"],
    ["not_authenticated", "● Não conectado"],
    ["error", "● Indisponível"],
  ] as const)("maps %s runtime status explicitly", async (state, label) => {
    render(<ProjectRuntimePanel {...props} service={service({ status: vi.fn().mockResolvedValue({ ...ready, installed: state !== "not_installed", authenticated: false, ready: false, state }) })} />);
    expect(await screen.findByText(label)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Executar com Codex" })).toBeNull();
  });

  it("shows loading and retries a failed status request", async () => {
    let rejectFirst!: (reason?: unknown) => void;
    const pendingStatus = new Promise<typeof ready>((_resolve, reject) => { rejectFirst = reject; });
    const status = vi.fn().mockImplementationOnce(() => pendingStatus).mockResolvedValueOnce(ready);
    render(<ProjectRuntimePanel {...props} service={service({ status })} />);
    await screen.findByRole("button", { name: "Pilot session" });
    expect(await screen.findByText("● Carregando status do Codex...")).toBeTruthy();
    await act(async () => { rejectFirst(new Error("offline")); });
    fireEvent.click(await screen.findByRole("button", { name: "Verificar novamente" }));
    expect(await screen.findByText("● Pronto")).toBeTruthy();
    expect((screen.getByLabelText("Tarefa") as HTMLTextAreaElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Executar com Codex" }) as HTMLButtonElement).disabled).toBe(false);
    expect(status).toHaveBeenCalledTimes(2);
  });

  it("accepts state ready as complementary readiness", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ status: vi.fn().mockResolvedValue({ ...ready, ready: false, state: "ready" }) })} />);
    expect(await screen.findByText("● Pronto")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Executar com Codex" })).toBeTruthy();
  });

  it("validates, submits once and renders real result and usage", async () => {
    const api = service();
    render(<ProjectRuntimePanel {...props} service={api} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Descreva a tarefa");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: " Inspect " } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(api.execute).toHaveBeenCalledWith("p-1", "s-1", "Inspect", "read_only");
    expect(screen.queryByText(/Usando contexto de/)).toBeNull();
  });

  it("keeps a successful execution when history refresh succeeds", async () => {
    const listExecutions = vi.fn().mockResolvedValue([]);
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(listExecutions).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(/O Codex não conseguiu concluir/)).toBeNull();
  });

  it("preserves a read-only result when navigation syncs the already selected session", async () => {
    const persisted = {
      ...failedExecution,
      execution_id: "e-1",
      status: "succeeded" as const,
      execution_mode: "read_only" as const,
      output: "Project structure",
      error_code: null,
    };
    const api = service({ getExecution: vi.fn().mockResolvedValue(persisted) });
    const onNavigate = vi.fn();
    const view = render(
      <ProjectRuntimePanel {...props} service={api} onNavigate={onNavigate} />,
    );
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(onNavigate).toHaveBeenCalledWith("s-1", "e-1");

    view.rerender(
      <ProjectRuntimePanel {...props} service={api} initialSessionId="s-1" initialExecutionId="e-1" onNavigate={onNavigate} />,
    );

    expect((await screen.findAllByText("Project structure")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Fase persistida: Finalizada com sucesso")).toBeTruthy();
    expect(api.listSessions).toHaveBeenCalledTimes(2);
  });

  it("preserves a workspace-write result when navigation syncs its execution", async () => {
    const persisted = {
      ...failedExecution,
      execution_id: "e-1",
      status: "succeeded" as const,
      output: "Project structure",
      error_code: null,
    };
    const api = service({ getExecution: vi.fn().mockResolvedValue(persisted) });
    const view = render(<ProjectRuntimePanel {...props} service={api} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();

    view.rerender(
      <ProjectRuntimePanel {...props} service={api} initialSessionId="s-1" initialExecutionId="e-1" />,
    );

    expect((await screen.findAllByText("Project structure")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Fase persistida: Finalizada com sucesso")).toBeTruthy();
  });

  it("keeps a successful execution visible when history refresh fails", async () => {
    const listExecutions = vi.fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("history offline"));
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(await screen.findByText(/execução foi concluída, mas o histórico/i)).toBeTruthy();
    expect(screen.queryByText(/O Codex não conseguiu concluir/)).toBeNull();
  });

  it("keeps a successful execution visible when memory refresh fails", async () => {
    const listMemory = vi.fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("memory offline"));
    render(<ProjectRuntimePanel {...props} service={service({ listMemory })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(await screen.findByText(/execução foi concluída, mas a memória/i)).toBeTruthy();
    expect(screen.queryByText(/O Codex não conseguiu concluir/)).toBeNull();
  });

  it("reports a real execute failure without inventing a successful result", async () => {
    const execute = vi.fn().mockRejectedValue(new ApiHttpError(400, "RUNTIME_FAILED", "runtime failed"));
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText(/O Codex não conseguiu concluir/)).toBeTruthy();
    expect(screen.queryByText("Project structure")).toBeNull();
  });

  it("reports an uncertain state on execute timeout and preserves a known result", async () => {
    const execute = vi.fn()
      .mockResolvedValueOnce(result)
      .mockRejectedValueOnce(new ApiTimeoutError(600_000, new Error("abort")));
    const listExecutions = vi.fn().mockResolvedValue([]);
    render(<ProjectRuntimePanel {...props} service={service({ execute, listExecutions })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText(/pode continuar sendo processada no servidor/i)).toBeTruthy();
    expect(screen.getByText("Project structure")).toBeTruthy();
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
    expect(listExecutions).toHaveBeenCalledTimes(3);
  });

  it("reports an uncertain state when the network is interrupted", async () => {
    const execute = vi.fn().mockRejectedValue(
      new ApiNetworkError("offline", new TypeError("network")),
    );
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText(/comunicação com o servidor foi interrompida/i)).toBeTruthy();
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
  });

  it("uses uncertain timeout semantics while preparing workspace-write", async () => {
    const prepare = vi.fn().mockRejectedValue(
      new ApiTimeoutError(600_000, new Error("abort")),
    );
    render(<ProjectRuntimePanel {...props} service={service({ prepare })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));

    expect(await screen.findByText(/pode continuar sendo processada no servidor/i)).toBeTruthy();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("uses uncertain timeout semantics after workspace-write approval", async () => {
    const approve = vi.fn().mockRejectedValue(
      new ApiTimeoutError(600_000, new Error("abort")),
    );
    render(<ProjectRuntimePanel {...props} service={service({ approve })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));

    expect(await screen.findByText(/interrompida antes de confirmar o resultado/i)).toBeTruthy();
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
  });

  it("reconciles a succeeded approve after an HTTP 5xx response", async () => {
    const persisted = { ...failedExecution, execution_id: "e-1", status: "succeeded" as const, output: "Persisted success", error_code: null };
    const api = service({
      approve: vi.fn().mockRejectedValue(new ApiHttpError(504, "GATEWAY_TIMEOUT", "timeout")),
      getExecution: vi.fn().mockResolvedValue(persisted),
      listExecutions: vi.fn().mockResolvedValue([persisted]),
    });
    render(<ProjectRuntimePanel {...props} service={api} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));

    expect(await screen.findByText("Persisted success")).toBeTruthy();
    expect(api.getExecution).toHaveBeenCalledWith("p-1", "e-1");
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
  });

  it("reports a confirmed failed approve after reconciliation", async () => {
    const approve = vi.fn().mockRejectedValue(new ApiHttpError(500, "UPSTREAM", "failed"));
    render(<ProjectRuntimePanel {...props} service={service({ approve, getExecution: vi.fn().mockResolvedValue({ ...failedExecution, execution_id: "e-1" }) })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));
    expect(await screen.findByText(/execução com falha permanece/i)).toBeTruthy();
  });

  it.each([
    ["not found", vi.fn().mockRejectedValue(new ApiHttpError(404, "NOT_FOUND", "missing"))],
    ["lookup unavailable", vi.fn().mockRejectedValue(new Error("offline"))],
  ])("keeps approve uncertain when reconciliation is %s", async (_case, getExecution) => {
    render(<ProjectRuntimePanel {...props} service={service({ approve: vi.fn().mockRejectedValue(new ApiHttpError(503, "UPSTREAM", "failed")), getExecution })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));
    expect(await screen.findByText(/interrompida antes de confirmar o resultado/i)).toBeTruthy();
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
  });

  it("preserves reconciled success when secondary refreshes and navigation fail", async () => {
    const persisted = { ...failedExecution, execution_id: "e-1", status: "succeeded" as const, output: "Recovered result", error_code: null };
    const listExecutions = vi.fn().mockResolvedValueOnce([]).mockRejectedValueOnce(new Error("history"));
    const listMemory = vi.fn().mockResolvedValueOnce([]).mockRejectedValueOnce(new Error("memory"));
    render(<ProjectRuntimePanel {...props} service={service({ approve: vi.fn().mockRejectedValue(new ApiHttpError(502, "UPSTREAM", "failed")), getExecution: vi.fn().mockResolvedValue(persisted), listExecutions, listMemory })} onNavigate={() => { throw new Error("navigation"); }} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));
    expect(await screen.findByText("Recovered result")).toBeTruthy();
    expect(await screen.findByText(/histórico não pôde ser atualizado/i)).toBeTruthy();
    expect(await screen.findByText(/memória da sessão não pôde ser atualizada/i)).toBeTruthy();
    expect(await screen.findByText(/navegação não pôde ser atualizada/i)).toBeTruthy();
  });

  it("treats execute HTTP 5xx as uncertain without unsafe history correlation", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ execute: vi.fn().mockRejectedValue(new ApiHttpError(504, "GATEWAY_TIMEOUT", "timeout")) })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText(/interrompida antes de confirmar o resultado/i)).toBeTruthy();
    expect(screen.queryByText(/execução com falha permanece/i)).toBeNull();
  });

  it("renders a large valid output without imposing an arbitrary limit", async () => {
    const output = `Large plan ${"x".repeat(250_000)}`;
    render(<ProjectRuntimePanel {...props} service={service({ execute: vi.fn().mockResolvedValue({ ...result, output }) })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText(output)).toBeTruthy();
  });

  it("keeps an approved workspace-write result when refresh fails", async () => {
    const listExecutions = vi.fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("history offline"));
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Write safely" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));

    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(await screen.findByText(/execução foi concluída, mas o histórico/i)).toBeTruthy();
    expect(screen.queryByText(/O Codex não conseguiu concluir/)).toBeNull();
  });

  it("keeps a successful result when navigation fails", async () => {
    const onNavigate = vi.fn(() => { throw new Error("navigation failed"); });
    render(<ProjectRuntimePanel {...props} service={service()} onNavigate={onNavigate} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));

    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(await screen.findByText(/execução foi concluída, mas a navegação/i)).toBeTruthy();
    expect(screen.queryByText(/O Codex não conseguiu concluir/)).toBeNull();
  });

  it("preserves input after failure and allows retry", async () => {
    const execute = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(result);
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Inspect" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByLabelText("Tarefa") as HTMLTextAreaElement).value).toBe("Inspect");
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText("Project structure")).toBeTruthy();
    expect(execute).toHaveBeenCalledTimes(2);
  });

  it("requires explicit confirmation before workspace write", async () => {
    const writeResult = { ...result, execution_mode: "workspace_write" as const, changes: [
      { path: "src/new.ts", change_type: "created" as const, size_before: null, size_after: 12 },
      { path: "src/changed.ts", change_type: "modified" as const, size_before: 4, size_after: 8 },
      { path: "src/old.ts", change_type: "deleted" as const, size_before: 5, size_after: null },
    ] };
    const prepare = vi.fn().mockImplementation(async (_projectId, _sessionId, instruction) => ({ ...(await service().prepare("p-1", "s-1", instruction)), instruction }));
    const approve = vi.fn().mockResolvedValue(writeResult);
    const cancel = vi.fn().mockResolvedValue(failedExecution);
    render(<ProjectRuntimePanel {...props} service={service({ prepare, approve, cancel })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: " Write safely " } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    expect(approve).not.toHaveBeenCalled();
    const confirmation = await screen.findByRole("alertdialog");
    expect(confirmation.textContent).toContain("Pilot");
    expect(confirmation.textContent).toContain("workspace-1");
    expect(confirmation.textContent).toContain("workspace ainda não foi alterado");
    expect(confirmation.textContent).toContain("typecheck");
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(approve).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button", { name: "Preparar plano" }));
    expect(cancel).toHaveBeenCalledWith("p-1", "e-1", "s-1", "Write safely");
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));
    expect(await screen.findByText("src/new.ts")).toBeTruthy();
    expect(screen.getByText("src/changed.ts")).toBeTruthy();
    expect(screen.getByText("src/old.ts")).toBeTruthy();
    expect((screen.getByLabelText("Permitir alterações no projeto") as HTMLInputElement).checked).toBe(true);
    expect(prepare).toHaveBeenCalledWith("p-1", "s-1", "Write safely", { engineering_phase: "planning", sprint_id: undefined, sprint_name: undefined, dependency_requests: [] });
    expect(approve).toHaveBeenCalledOnce();
    expect(approve).toHaveBeenCalledWith("p-1", "e-1", "s-1", "Write safely", { engineering_phase: "planning", sprint_id: undefined, sprint_name: undefined, dependency_requests: [] });
  });

  it("renders bounded engineering plan, validation, repair and quality evidence", async () => {
    const engineeringResult = {
      ...result,
      execution_mode: "workspace_write" as const,
      status: "succeeded" as const,
      instruction: "Add health endpoint",
      operational_plan: { execution_id: "e-1", created_at: "2026-08-12T00:00:00Z", source: "ai", steps: [
        { step_id: "execute", operation: "execute_workspace_task", description: "Executar a tarefa no workspace.", dependencies: [], target_hints: ["src/api.py"], validation_hints: ["pytest"] },
      ] },
      step_results: [
        { execution_id: "e-1", step_id: "execute", executor: "developer_agent", tool_id: "workspace_changes", succeeded: true, output: "Updated src/api.py", started_at: "2026-08-12T00:00:00Z", completed_at: "2026-08-12T00:00:01Z" },
      ],
      validations: [
        { execution_id: "e-1", sequence: 2, validator: "vitest", command: ["npm", "run", "test"], exit_code: 0, status: "passed" as const, output: "vitest passed", completed_at: "2026-08-12T00:00:02Z" },
        { execution_id: "e-1", sequence: 1, validator: "pytest", command: ["python", "-m", "pytest", "tests"], exit_code: 1, status: "failed" as const, output: "1 failed", completed_at: "2026-08-12T00:00:01Z" },
      ],
      repair: { execution_id: "e-1", outcome: "succeeded" as const, attempt_count: 1 },
      quality_gate: { gate_id: "PROJECT-ENGINEERING-VALIDATION", execution_id: "e-1", stage_id: "validation", decision: "APPROVED" as const, satisfied_criteria: ["pytest passed", "vitest passed"], unsatisfied_criteria: [], evaluated_at: "2026-08-12T00:00:03Z" },
    } satisfies ProjectAIRuntimeExecutionDto;
    render(<ProjectRuntimePanel {...props} service={service({ approve: vi.fn().mockResolvedValue(engineeringResult) })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Add health endpoint" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar plano" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aprovar e executar" }));

    expect(await screen.findByRole("region", { name: "Evidências da execução de engenharia" })).toBeTruthy();
    expect(screen.getByText("e-1")).toBeTruthy();
    expect(screen.getByText("Executar a tarefa no workspace.")).toBeTruthy();
    expect(screen.getByText("Concluída: execute")).toBeTruthy();
    expect(screen.getByText("Updated src/api.py")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Testes" })).toBeTruthy();
    expect(screen.getByText("Testes Python")).toBeTruthy();
    expect(screen.getByText("Testes Vitest")).toBeTruthy();
    expect(screen.getByText("pytest")).toBeTruthy();
    expect(screen.getByText("vitest")).toBeTruthy();
    expect(screen.getByText("1 tentativa(s) · Concluído")).toBeTruthy();
    expect(screen.getAllByText("Aprovado")).toHaveLength(2);
    expect(screen.getByText("pytest passed")).toBeTruthy();
    expect(screen.getAllByText("vitest passed")).toHaveLength(2);
    expect(screen.getByText("Nenhum critério não atendido.")).toBeTruthy();
  });

  it("reopens a persisted BLOCKED execution with failure evidence", async () => {
    const blocked = {
      ...failedExecution,
      execution_id: "e-blocked",
      error_code: "QUALITY_GATE_BLOCKED",
      operational_plan: { execution_id: "e-blocked", created_at: "2026-08-12T00:00:00Z", source: "deterministic", steps: [] },
      step_results: [],
      validations: [{ execution_id: "e-blocked", sequence: 1, validator: "eslint", command: ["npm", "run", "lint"], exit_code: 1, status: "failed" as const, output: "lint failed", completed_at: "2026-08-12T00:00:01Z" }],
      repair: { execution_id: "e-blocked", outcome: "exhausted" as const, attempt_count: 2 },
      quality_gate: { gate_id: "gate-1", execution_id: "e-blocked", stage_id: "validation", decision: "BLOCKED" as const, satisfied_criteria: [], unsatisfied_criteria: ["eslint must pass"], evaluated_at: "2026-08-12T00:00:02Z" },
    } satisfies ProjectExecutionDto;
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions: vi.fn().mockResolvedValue([blocked]) })} />);
    fireEvent.click(await screen.findByRole("button", { name: /falhou.*change file/i }));
    expect(await screen.findByText("e-blocked")).toBeTruthy();
    expect(screen.getByText("ESLint")).toBeTruthy();
    expect(screen.getByText("eslint")).toBeTruthy();
    expect(screen.getByText("2 tentativa(s) · Tentativas esgotadas")).toBeTruthy();
    expect(screen.getAllByText("Bloqueado")).toHaveLength(2);
    expect(screen.getByText("eslint must pass")).toBeTruthy();
    expect(screen.getByText(/QUALITY_GATE_BLOCKED/)).toBeTruthy();
  });

  it("creates and selects a session while preserving input on error", async () => {
    const createSession = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce({ ...session, session_id: "s-2", title: "New work" });
    render(<ProjectRuntimePanel {...props} service={service({ listSessions: vi.fn().mockResolvedValue([]), createSession })} />);
    expect(await screen.findByText("Nenhuma sessão ainda.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Nome da sessão"), { target: { value: " New work " } });
    fireEvent.click(screen.getByRole("button", { name: "Nova sessão" }));
    expect(await screen.findByText(/não foi possível criar a sessão/i)).toBeTruthy();
    expect((screen.getByLabelText("Nome da sessão") as HTMLInputElement).value).toBe(" New work ");
    fireEvent.click(screen.getByRole("button", { name: "Nova sessão" }));
    expect(await screen.findByRole("button", { name: "New work" })).toBeTruthy();
    expect(createSession).toHaveBeenLastCalledWith("p-1", "New work");
  });

  it("shows persisted failed history, usage, changes and details", async () => {
    render(<ProjectRuntimePanel {...props} service={service({ listExecutions: vi.fn().mockResolvedValue([failedExecution]) })} />);
    const historyItem = await screen.findByRole("button", {
      name: /falhou.*codex.*permitir alterações.*change file.*1 arquivos alterados.*10 tokens de entrada.*2 tokens de saída/i,
    });
    expect(historyItem.textContent).toContain("Change file");
    expect(historyItem.textContent).toContain("10 tokens de entrada");
    expect(historyItem.textContent).toContain("2 tokens de saída");
    fireEvent.click(historyItem);
    expect(await screen.findByText("AI_RUNTIME_TIMEOUT")).toBeTruthy();
    expect(screen.getByText("partial.txt")).toBeTruthy();
    expect(screen.getByText(/Usando contexto de 2 execuções anteriores/)).toBeTruthy();
    expect(screen.getByText(/Tamanho do contexto: 17.4 mil caracteres/)).toBeTruthy();
    expect(screen.getByText(/9 execuções anteriores omitidas/)).toBeTruthy();
    expect(screen.getByText(/O contexto recente foi compactado/)).toBeTruthy();
  });

  it("shows context observability without sending history from the frontend", async () => {
    const execute = vi.fn().mockResolvedValue({ ...result, context_entry_count: 1, context_truncated: true });
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Continue" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText(/Usando contexto de 1 execução anterior/)).toBeTruthy();
    expect(screen.getByText(/Tamanho do contexto: 79 caracteres/)).toBeTruthy();
    expect(screen.getByText(/O contexto recente foi compactado/)).toBeTruthy();
    expect(execute).toHaveBeenCalledWith("p-1", "s-1", "Continue", "read_only");
  });

  it("clears result context observability when another session is selected", async () => {
    const other = { ...session, session_id: "s-2", title: "Isolated session" };
    const execute = vi.fn().mockResolvedValue({ ...result, context_entry_count: 1 });
    render(<ProjectRuntimePanel {...props} service={service({
      execute, listSessions: vi.fn().mockResolvedValue([session, other]),
    })} />);
    await screen.findByText("● Pronto");
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Continue" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(await screen.findByText(/Usando contexto de 1 execução anterior/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Isolated session" }));
    expect(screen.queryByText(/Usando contexto de/)).toBeNull();
    expect(screen.queryByText("Project structure")).toBeNull();
  });

  it("serializes every memory kind separately from trimmed content", async () => {
    const addMemory = vi.fn().mockImplementation(async (_projectId: string, _sessionId: string, kind: SessionMemoryKind, content: string) => ({ memory_id: `m-${kind}`, session_id: "s-1", project_id: "p-1", kind, content, source_execution_id: null, created_at: "2026-08-10T00:00:00Z" }));
    render(<ProjectRuntimePanel {...props} service={service({ addMemory })} />);
    expect(await screen.findByText("Nenhuma memória nesta sessão.")).toBeTruthy();
    expect((screen.getByLabelText("Tipo") as HTMLSelectElement).value).toBe("fact");
    const cases = [
      ["fact", "Default fact"],
      ["constraint", "Use PostgreSQL for persistence."],
      ["decision", "Keep the REST API"],
      ["artifact", "Created src/customer.ts"],
      ["goal", "Ship customer validation"],
    ] as const;
    for (const [kind, content] of cases) {
      fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: kind } });
      fireEvent.change(screen.getByLabelText("Memória"), { target: { value: `  ${content}  ` } });
      fireEvent.click(screen.getByRole("button", { name: "Adicionar memória" }));
      expect(await screen.findByText(content)).toBeTruthy();
      expect(addMemory).toHaveBeenLastCalledWith("p-1", "s-1", kind, content);
    }
    expect(screen.getAllByText("Manual")).toHaveLength(cases.length);
  });

  it("rejects empty memory and preserves input when adding fails", async () => {
    const addMemory = vi.fn().mockRejectedValue(new Error("offline"));
    render(<ProjectRuntimePanel {...props} service={service({ addMemory })} />);
    await screen.findByText("Nenhuma memória nesta sessão.");
    fireEvent.change(screen.getByLabelText("Memória"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar memória" }));
    expect(await screen.findByText("Informe o conteúdo da memória.")).toBeTruthy();
    expect(addMemory).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "decision" } });
    fireEvent.change(screen.getByLabelText("Memória"), { target: { value: " Keep this input " } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar memória" }));
    expect(await screen.findByText("Não foi possível adicionar a memória.")).toBeTruthy();
    expect((screen.getByLabelText("Memória") as HTMLInputElement).value).toBe(" Keep this input ");
    expect(addMemory).toHaveBeenCalledWith("p-1", "s-1", "decision", "Keep this input");
  });

  it("clears memory on session change and ignores a stale response", async () => {
    const other = { ...session, session_id: "s-2", title: "Empty session" };
    const stale = { memory_id: "m-old", session_id: "s-1", project_id: "p-1", kind: "fact" as const, content: "Stale memory", source_execution_id: null, created_at: "2026-08-10T00:00:00Z" };
    let resolveOld!: (items: ReadonlyArray<typeof stale>) => void;
    let resolveCurrent!: (items: ReadonlyArray<typeof stale>) => void;
    const listMemory = vi.fn()
      .mockImplementationOnce(() => new Promise<ReadonlyArray<typeof stale>>((resolve) => { resolveOld = resolve; }))
      .mockImplementationOnce(() => new Promise<ReadonlyArray<typeof stale>>((resolve) => { resolveCurrent = resolve; }));
    render(<ProjectRuntimePanel {...props} service={service({ listSessions: vi.fn().mockResolvedValue([session, other]), listMemory })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Empty session" }));
    expect(screen.getByText("Carregando memória...")).toBeTruthy();
    await act(async () => { resolveCurrent([]); });
    expect(await screen.findByText("Nenhuma memória nesta sessão.")).toBeTruthy();
    await act(async () => { resolveOld([stale]); });
    expect(screen.queryByText("Stale memory")).toBeNull();
    expect(screen.getByText("Nenhuma memória nesta sessão.")).toBeTruthy();
  });
});
