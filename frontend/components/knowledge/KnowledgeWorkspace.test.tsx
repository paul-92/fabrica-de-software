// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProjectDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind } from "../../lib/api/dtos";
import type { KnowledgeLoader } from "../../lib/services/knowledge";
import { KnowledgeWorkspace } from "./KnowledgeWorkspace";

afterEach(cleanup);

const project = (id: string, name = id): ProjectDto => ({ project_id: id, name, workspace_path: `C:/${id}`, created_at: "2026-08-01T12:00:00Z", updated_at: "2026-08-01T12:00:00Z" });
const session = (id: string, projectId: string, title = id): ProjectSessionDto => ({ session_id: id, project_id: projectId, title, created_at: "2026-08-02T12:00:00Z", updated_at: "2026-08-10T12:00:00Z" });
const memory = (id: string, kind: SessionMemoryKind, content: string, source: string | null = null): SessionMemoryDto => ({ memory_id: id, session_id: "s-1", project_id: "p-1", kind, content, source_execution_id: source, created_at: "2026-08-10T12:00:00Z" });

function loader(overrides: Partial<KnowledgeLoader> = {}): KnowledgeLoader {
  return {
    listProjects: vi.fn().mockResolvedValue([project("p-1", "Projeto um")]),
    listSessions: vi.fn().mockResolvedValue([session("s-1", "p-1", "Sessão um")]),
    listMemory: vi.fn().mockResolvedValue([]),
    ...overrides,
  };
}

async function selectFirstProjectAndSession() {
  fireEvent.click(await screen.findByRole("button", { name: /Projeto um.*p-1/i }));
  fireEvent.click(await screen.findByRole("button", { name: /Sessão um/i }));
}

describe("KnowledgeWorkspace", () => {
  it("announces initial loading and shows an empty project state", async () => {
    let resolve!: (items: readonly ProjectDto[]) => void;
    const view = render(<KnowledgeWorkspace loader={loader({ listProjects: vi.fn(() => new Promise<readonly ProjectDto[]>((done) => { resolve = done; })) })} />);
    expect(screen.getByRole("status").textContent).toContain("Carregando projetos");
    await act(async () => { resolve([]); });
    expect(await screen.findByText("Nenhum projeto ainda")).toBeTruthy();
    view.unmount();
  });

  it("shows a safe project error and retries", async () => {
    const listProjects = vi.fn().mockRejectedValueOnce(new Error("secret")).mockResolvedValueOnce([]);
    render(<KnowledgeWorkspace loader={loader({ listProjects })} />);
    expect((await screen.findByRole("alert")).textContent).toContain("Projetos indisponíveis");
    expect(document.body.textContent).not.toContain("secret");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhum projeto ainda")).toBeTruthy();
    expect(listProjects).toHaveBeenCalledTimes(2);
  });

  it("loads sessions and handles their empty and error states", async () => {
    const listSessions = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]);
    render(<KnowledgeWorkspace loader={loader({ listSessions })} />);
    fireEvent.click(await screen.findByRole("button", { name: /Projeto um.*p-1/i }));
    expect(screen.getByText("Carregando sessões...")).toBeTruthy();
    expect((await screen.findByRole("alert")).textContent).toContain("Sessões indisponíveis");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma sessão neste projeto.")).toBeTruthy();
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

  it("renders every memory kind, dates and manual or automatic origin", async () => {
    const entries = [
      memory("m-1", "fact", "Fato registrado"),
      memory("m-2", "decision", "Decisão registrada", "execution-2"),
      memory("m-3", "constraint", "Restrição registrada"),
      memory("m-4", "artifact", "Artefato registrado"),
      memory("m-5", "goal", "Objetivo registrado"),
    ];
    const api = loader({ listMemory: vi.fn().mockResolvedValue(entries) });
    render(<KnowledgeWorkspace loader={api} />);
    await selectFirstProjectAndSession();
    expect(screen.getByText("Carregando memórias...")).toBeTruthy();
    expect(await screen.findByText("Fato registrado")).toBeTruthy();
    for (const label of ["Fato", "Decisão", "Restrição", "Artefato", "Objetivo"]) expect(screen.getByText(label)).toBeTruthy();
    expect(screen.getAllByText("Origem manual")).toHaveLength(4);
    expect(screen.getByText("Execução execution-2")).toBeTruthy();
    expect(screen.getAllByText(/10 de ago.*2026/i).length).toBeGreaterThan(0);
    expect(api.listMemory).toHaveBeenCalledWith("p-1", "s-1");
  });

  it("handles empty memory, a safe error and retry", async () => {
    const listMemory = vi.fn().mockRejectedValueOnce(new Error("private detail")).mockResolvedValueOnce([]);
    render(<KnowledgeWorkspace loader={loader({ listMemory })} />);
    await selectFirstProjectAndSession();
    expect((await screen.findByRole("alert")).textContent).toContain("Memórias indisponíveis");
    expect(document.body.textContent).not.toContain("private detail");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma memória nesta sessão.")).toBeTruthy();
    expect(listMemory).toHaveBeenCalledTimes(2);
  });

  it("clears old selections and ignores stale session and memory responses", async () => {
    const projects = [project("p-1", "Projeto um"), project("p-2", "Projeto dois")];
    const firstSession = session("s-1", "p-1", "Sessão um");
    const secondSession = session("s-2", "p-2", "Sessão dois");
    let resolveOldSessions!: (items: readonly ProjectSessionDto[]) => void;
    let resolveOldMemory!: (items: readonly SessionMemoryDto[]) => void;
    const listSessions = vi.fn()
      .mockImplementationOnce(() => new Promise<readonly ProjectSessionDto[]>((done) => { resolveOldSessions = done; }))
      .mockResolvedValueOnce([secondSession])
      .mockResolvedValueOnce([firstSession])
      .mockResolvedValueOnce([secondSession]);
    const listMemory = vi.fn()
      .mockImplementationOnce(() => new Promise<readonly SessionMemoryDto[]>((done) => { resolveOldMemory = done; }))
      .mockResolvedValueOnce([]);
    render(<KnowledgeWorkspace loader={loader({ listProjects: vi.fn().mockResolvedValue(projects), listSessions, listMemory })} />);

    fireEvent.click(await screen.findByRole("button", { name: /Projeto um.*p-1/i }));
    fireEvent.click(screen.getByRole("button", { name: /Projeto dois.*p-2/i }));
    expect(await screen.findByRole("button", { name: /Sessão dois/i })).toBeTruthy();
    await act(async () => { resolveOldSessions([firstSession]); });
    expect(screen.queryByRole("button", { name: /Sessão um/i })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Projeto um.*p-1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Sessão um/i }));
    fireEvent.click(screen.getByRole("button", { name: /Projeto dois.*p-2/i }));
    expect(screen.queryByText("Memórias da sessão")).toBeNull();
    await act(async () => { resolveOldMemory([memory("stale", "fact", "Memória antiga")]); });
    expect(screen.queryByText("Memória antiga")).toBeNull();
    await waitFor(() => expect(listSessions).toHaveBeenCalledTimes(4));
  });
});
