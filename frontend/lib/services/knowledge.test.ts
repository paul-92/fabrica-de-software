import { describe, expect, it, vi } from "vitest";
import type { PlatformClients } from "../api";
import { createKnowledgeLoader, KnowledgeDataService } from "./knowledge";

describe("KnowledgeDataService", () => {
  it("delegates projects, sessions and memory to the public clients", async () => {
    const projects = [{ project_id: "p-1" }];
    const sessions = [{ session_id: "s-1" }];
    const memory = [{ memory_id: "m-1" }];
    const clients = {
      projects: { list: vi.fn().mockResolvedValue(projects) },
      projectHistory: {
        listSessions: vi.fn().mockResolvedValue(sessions),
        listMemory: vi.fn().mockResolvedValue(memory),
      },
    } as unknown as Pick<PlatformClients, "projects" | "projectHistory">;
    const service = new KnowledgeDataService(clients);

    expect(await service.listProjects()).toBe(projects);
    expect(await service.listSessions("p/1")).toBe(sessions);
    expect(await service.listMemory("p/1", "s/1")).toBe(memory);
    expect(clients.projectHistory.listSessions).toHaveBeenCalledWith("p/1");
    expect(clients.projectHistory.listMemory).toHaveBeenCalledWith("p/1", "s/1");
  });

  it("initializes platform clients lazily and only once", async () => {
    const clientsFactory = vi.fn().mockReturnValue({
      projects: { list: vi.fn().mockResolvedValue([]) },
      projectHistory: { listSessions: vi.fn().mockResolvedValue([]), listMemory: vi.fn().mockResolvedValue([]) },
    });
    const loader = createKnowledgeLoader(clientsFactory);

    expect(clientsFactory).not.toHaveBeenCalled();
    await loader.listProjects();
    await loader.listSessions("p-1");
    await loader.listMemory("p-1", "s-1");
    expect(clientsFactory).toHaveBeenCalledOnce();
  });
});
