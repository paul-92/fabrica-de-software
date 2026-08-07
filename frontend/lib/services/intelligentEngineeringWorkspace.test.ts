import { describe, expect, it, vi } from "vitest";
import type { IntelligentEngineeringRequestDto, IntelligentEngineeringResponseDto } from "../api/dtos";
import { createIntelligentEngineeringWorkspaceExecutor, IntelligentEngineeringWorkspaceService } from "./intelligentEngineeringWorkspace";

const request = { planning_request: { goal: "Repair", context: { objective: "Fix" } }, knowledge_context: { knowledge_count: 0 }, engineering_request: { analysis: { summary: "Failure" }, replacement_contents: { "app.py": "fixed" } } } satisfies IntelligentEngineeringRequestDto;
const response = { planning_request: request.planning_request } as IntelligentEngineeringResponseDto;

describe("IntelligentEngineeringWorkspaceService", () => {
  it("preserves the request and response while delegating once", async () => {
    const client = { execute: vi.fn().mockResolvedValue(response) };
    const result = await new IntelligentEngineeringWorkspaceService(client).execute(request);
    expect(client.execute).toHaveBeenCalledWith(request);
    expect(result).toBe(response);
  });

  it("initializes platform clients lazily and only once", async () => {
    const execute = vi.fn().mockResolvedValue(response);
    const factory = vi.fn(() => ({ intelligentEngineering: { execute } }));
    const executor = createIntelligentEngineeringWorkspaceExecutor(factory);
    expect(factory).not.toHaveBeenCalled();
    await executor.execute(request);
    await executor.execute(request);
    expect(factory).toHaveBeenCalledOnce();
  });
});
