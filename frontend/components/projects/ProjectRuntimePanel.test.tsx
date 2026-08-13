// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectAIRuntimeExecutionDto, ProjectExecutionDto, SessionMemoryKind } from "../../lib/api/dtos";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

afterEach(cleanup);
const ready = { runtime_id: "codex", installed: true, authenticated: true, ready: true, state: "ready" as const, version: "1", message: "Ready", authentication_command: null };
const result = { execution_id: "e-1", output: "Project structure", runtime_id: "codex", model_id: "model", usage: { input_units: 4, output_units: 2, total_units: 6, cost: null }, metadata: {}, execution_mode: "read_only" as const, changes: [], context_entry_count: 0, context_truncated: false, context_char_count: 79, context_omitted_execution_count: 0, memory_entry_count: 0, memory_char_count: 49, memory_truncated: false };
const session = { session_id: "s-1", project_id: "p-1", title: "Pilot session", created_at: "2026-08-07T00:00:00Z", updated_at: "2026-08-07T00:00:00Z" };
const failedExecution = { execution_id: "e-failed", session_id: "s-1", project_id: "p-1", runtime_id: "codex", instruction: "Change file", execution_mode: "workspace_write" as const, status: "failed" as const, output: null, model: null, usage: { input_units: 10, output_units: 2, total_units: 12, cost: null }, changes: [{ path: "partial.txt", change_type: "created" as const, size_before: null, size_after: 2 }], error_code: "AI_RUNTIME_TIMEOUT", context_entry_count: 2, context_truncated: true, context_char_count: 17432, context_omitted_execution_count: 9, memory_entry_count: 1, memory_char_count: 120, memory_truncated: false, created_at: "2026-08-07T00:00:00Z", completed_at: "2026-08-07T00:00:01Z" };
const props = { projectId: "p-1", projectName: "Pilot", workspacePath: "C:/pilot" };
function service(overrides: Partial<ProjectRuntimeWorkspaceService> = {}): ProjectRuntimeWorkspaceService {
  return { status: vi.fn().mockResolvedValue(ready), execute: vi.fn().mockResolvedValue(result), listSessions: vi.fn().mockResolvedValue([session]), createSession: vi.fn().mockResolvedValue(session), listExecutions: vi.fn().mockResolvedValue([]), getExecution: vi.fn(), listMemory: vi.fn().mockResolvedValue([]), addMemory: vi.fn(), ...overrides };
}

describe("ProjectRuntimePanel", () => {
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
    const execute = vi.fn().mockResolvedValue(writeResult);
    render(<ProjectRuntimePanel {...props} service={service({ execute })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: " Write safely " } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    expect(execute).not.toHaveBeenCalled();
    const confirmation = await screen.findByRole("alertdialog");
    expect(confirmation.textContent).toContain("Pilot");
    expect(confirmation.textContent).toContain("C:/pilot");
    expect(confirmation.textContent).toContain("Permitir alterações");
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(execute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar e executar" }));
    expect(await screen.findByText("src/new.ts")).toBeTruthy();
    expect(screen.getByText("src/changed.ts")).toBeTruthy();
    expect(screen.getByText("src/old.ts")).toBeTruthy();
    expect((screen.getByLabelText("Permitir alterações no projeto") as HTMLInputElement).checked).toBe(true);
    expect(execute).toHaveBeenCalledOnce();
    expect(execute).toHaveBeenCalledWith("p-1", "s-1", "Write safely", "workspace_write");
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
    render(<ProjectRuntimePanel {...props} service={service({ execute: vi.fn().mockResolvedValue(engineeringResult) })} />);
    await screen.findByText("● Pronto");
    fireEvent.click(screen.getByLabelText("Permitir alterações no projeto"));
    fireEvent.change(screen.getByLabelText("Tarefa"), { target: { value: "Add health endpoint" } });
    fireEvent.click(screen.getByRole("button", { name: "Executar com Codex" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar e executar" }));

    expect(await screen.findByRole("region", { name: "Evidências da execução de engenharia" })).toBeTruthy();
    expect(screen.getByText("e-1")).toBeTruthy();
    expect(screen.getByText("Executar a tarefa no workspace.")).toBeTruthy();
    expect(screen.getByText("Concluída: execute")).toBeTruthy();
    expect(screen.getByText("Updated src/api.py")).toBeTruthy();
    const validationHeadings = screen.getAllByRole("heading", { level: 5 }).filter((heading) => heading.textContent?.startsWith("#"));
    expect(validationHeadings.map((heading) => heading.textContent)).toEqual(["#1 · pytest", "#2 · vitest"]);
    expect(screen.getByText("1 tentativa(s) · Concluído")).toBeTruthy();
    expect(screen.getByText("Aprovado")).toBeTruthy();
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
    expect(screen.getByText("#1 · eslint")).toBeTruthy();
    expect(screen.getByText("2 tentativa(s) · Tentativas esgotadas")).toBeTruthy();
    expect(screen.getByText("Bloqueado")).toBeTruthy();
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
