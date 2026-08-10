// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AgentCatalogItemDto } from "../../lib/api/dtos";
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

const loader = (listAgents: AgentsLoader["listAgents"]): AgentsLoader => ({
  listAgents,
});

describe("AgentsWorkspace", () => {
  it("announces loading and renders every public field accessibly", async () => {
    let resolve!: (items: readonly AgentCatalogItemDto[]) => void;
    const listAgents = vi.fn(
      () => new Promise<readonly AgentCatalogItemDto[]>((done) => { resolve = done; }),
    );
    render(<AgentsWorkspace loader={loader(listAgents)} />);

    expect(screen.getByRole("status").textContent).toContain("Carregando catálogo de agentes");

    await act(async () => { resolve([agent("backend-engineer")]); });

    expect(await screen.findByRole("heading", { name: "Backend Engineer" })).toBeTruthy();
    const catalog = screen.getByRole("region", { name: "Catálogo de agentes" });
    for (const text of [
      "backend-engineer", "0.1.0", "Engineering", "active",
      "validate-inputs", "produce-evidence",
    ]) expect(within(catalog).getByText(text)).toBeTruthy();
    expect(within(catalog).getByText("Status declarativo")).toBeTruthy();
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
});
