// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  AgentCatalogItemDto,
  AgentRuntimeProjectionDto,
} from "../../lib/api/dtos";
import type { AgentsLoader } from "../../lib/services/agents";
import { AgentsWorkspace } from "./AgentsWorkspace";

afterEach(cleanup);

const agent = (
  agentId: string,
  overrides: Partial<AgentCatalogItemDto> = {},
): AgentCatalogItemDto => ({
  agent_id: agentId,
  name: "Backend Engineer",
  version: "0.1.0",
  lifecycle_status: "active",
  department: "Engineering",
  capabilities: ["validate-inputs", "produce-evidence"],
  ...overrides,
});

const runtime = (
  agentId: string,
  overrides: Partial<AgentRuntimeProjectionDto> = {},
): AgentRuntimeProjectionDto => ({
  agent_id: agentId,
  registered: true,
  execution_count: 8,
  succeeded: 4,
  failed: 1,
  rejected: 2,
  cancelled: 3,
  timed_out: 5,
  retries: 6,
  ...overrides,
});

const loader = (
  listAgents: AgentsLoader["listAgents"],
  listRuntime: AgentsLoader["listRuntime"] = vi.fn().mockResolvedValue([]),
): AgentsLoader => ({
  listAgents,
  listRuntime,
});

describe("AgentsWorkspace", () => {
  it("announces loading and renders every public field accessibly", async () => {
    let resolve!: (items: readonly AgentCatalogItemDto[]) => void;
    const listAgents = vi.fn(
      () => new Promise<readonly AgentCatalogItemDto[]>((done) => { resolve = done; }),
    );
    render(<AgentsWorkspace loader={loader(
      listAgents,
      vi.fn().mockResolvedValue([runtime("backend-engineer")]),
    )} />);

    expect(screen.getByRole("status").textContent).toContain("Carregando catálogo de agentes");

    await act(async () => { resolve([agent("backend-engineer")]); });

    expect(await screen.findByRole("heading", { name: "Backend Engineer" })).toBeTruthy();
    const catalog = screen.getByRole("region", { name: "Catálogo de agentes" });
    for (const text of [
      "backend-engineer", "0.1.0", "Engineering", "active",
      "validate-inputs", "produce-evidence",
    ]) expect(within(catalog).getByText(text)).toBeTruthy();
    expect(within(catalog).getByText("Status declarativo")).toBeTruthy();
    const operational = within(catalog).getByRole("region", {
      name: "Dados operacionais observados",
    });
    for (const label of [
      "Registrado no runtime",
      "Execuções",
      "Concluídas",
      "Falhas",
      "Rejeitadas",
      "Canceladas",
      "Tempo esgotado",
      "Novas tentativas",
    ]) expect(within(operational).getByText(label)).toBeTruthy();
    expect(within(operational).getByText("Sim")).toBeTruthy();
    for (const unavailableMeaning of ["online", "offline", "disponível", "indisponível", "ready"]) {
      expect(catalog.textContent?.toLowerCase()).not.toContain(unavailableMeaning);
    }
  });

  it("shows agents in deterministic order and supports empty capabilities", async () => {
    render(<AgentsWorkspace loader={loader(vi.fn().mockResolvedValue([
      agent("alpha", { name: "Alpha", capabilities: [] }),
      agent("zeta", { name: "Zeta" }),
    ]))} />);

    const headings = await screen.findAllByRole("heading", { level: 2 });
    expect(headings.map((heading) => heading.textContent)).toEqual(["Alpha", "Zeta"]);
    expect(screen.getByText("Nenhuma capacidade declarada.")).toBeTruthy();
  });

  it("shows an empty catalog state", async () => {
    render(<AgentsWorkspace loader={loader(vi.fn().mockResolvedValue([]))} />);
    expect(await screen.findByRole("heading", { name: "Nenhum agente no catálogo" })).toBeTruthy();
  });

  it("shows a safe error and retries", async () => {
    const listAgents = vi.fn()
      .mockRejectedValueOnce(new Error("C:/private/registry/agents.yaml"))
      .mockResolvedValueOnce([agent("backend-engineer")]);
    render(<AgentsWorkspace loader={loader(listAgents)} />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Catálogo de agentes indisponível");
    expect(document.body.textContent).not.toContain("C:/private");

    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(screen.getByRole("status")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "Backend Engineer" })).toBeTruthy();
    await waitFor(() => expect(listAgents).toHaveBeenCalledTimes(2));
  });

  it("matches runtime metrics by agent_id instead of array position", async () => {
    render(<AgentsWorkspace loader={loader(
      vi.fn().mockResolvedValue([
        agent("alpha", { name: "Alpha" }),
        agent("zeta", { name: "Zeta" }),
      ]),
      vi.fn().mockResolvedValue([
        runtime("zeta", { execution_count: 22 }),
        runtime("alpha", { execution_count: 11 }),
      ]),
    )} />);

    const alphaCard = (await screen.findByRole("heading", { name: "Alpha" }))
      .closest("article");
    const zetaCard = screen.getByRole("heading", { name: "Zeta" })
      .closest("article");

    expect(within(alphaCard!).getByText("11")).toBeTruthy();
    expect(within(zetaCard!).getByText("22")).toBeTruthy();
  });

  it("keeps the catalog visible while runtime data is loading", async () => {
    const listRuntime = vi.fn(
      () => new Promise<readonly AgentRuntimeProjectionDto[]>(() => undefined),
    );
    render(<AgentsWorkspace loader={loader(
      vi.fn().mockResolvedValue([agent("reviewer")]),
      listRuntime,
    )} />);

    expect(await screen.findByRole("heading", { name: "Backend Engineer" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(
      "Carregando dados operacionais",
    );
  });

  it("keeps the catalog visible when runtime fails and retries only runtime", async () => {
    const listAgents = vi.fn().mockResolvedValue([agent("reviewer")]);
    const listRuntime = vi.fn()
      .mockRejectedValueOnce(new Error("operational failure"))
      .mockResolvedValueOnce([runtime("reviewer")]);
    render(<AgentsWorkspace loader={loader(listAgents, listRuntime)} />);

    expect(await screen.findByRole("heading", { name: "Backend Engineer" })).toBeTruthy();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Dados operacionais indisponíveis");

    fireEvent.click(screen.getByRole("button", {
      name: "Tentar métricas novamente",
    }));

    expect(await screen.findByText("Registrado no runtime")).toBeTruthy();
    expect(listAgents).toHaveBeenCalledOnce();
    expect(listRuntime).toHaveBeenCalledTimes(2);
  });

  it("does not fabricate metrics for a catalog agent missing from runtime", async () => {
    render(<AgentsWorkspace loader={loader(
      vi.fn().mockResolvedValue([agent("reviewer")]),
      vi.fn().mockResolvedValue([]),
    )} />);

    expect(await screen.findByText(
      "Sem observações operacionais para este agente.",
    )).toBeTruthy();
    const operational = screen.getByRole("region", {
      name: "Dados operacionais observados",
    });
    expect(within(operational).queryByText("Execuções")).toBeNull();
  });

  it("ignores runtime-only agents without fabricating catalog metadata", async () => {
    render(<AgentsWorkspace loader={loader(
      vi.fn().mockResolvedValue([agent("catalog-agent")]),
      vi.fn().mockResolvedValue([runtime("runtime-only")]),
    )} />);

    expect(await screen.findByText("catalog-agent")).toBeTruthy();
    expect(screen.queryByText("runtime-only")).toBeNull();
    expect(screen.getByText(
      "Sem observações operacionais para este agente.",
    )).toBeTruthy();
  });
});
