// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiHttpError } from "../../lib/api/errors";
import type { ProjectWorkspaceService } from "../../lib/services/projectWorkspaceService";
import { ProjectFilesPanel } from "./ProjectFilesPanel";

afterEach(cleanup);
const root = { path: "", entries: [{ path: "src", name: "src", kind: "directory" as const, size: null }, { path: "README.md", name: "README.md", kind: "file" as const, size: 5 }] };
function service(overrides: Partial<ProjectWorkspaceService> = {}): ProjectWorkspaceService { return { listDirectory: vi.fn().mockResolvedValue(root), readFile: vi.fn().mockResolvedValue({ path: "README.md", name: "README.md", content: "Olá\n", size: 6, language: "markdown", truncated: false }), ...overrides }; }

describe("ProjectFilesPanel", () => {
  it("loads root, expands lazily and opens a read-only file", async () => {
    const api = service({ listDirectory: vi.fn().mockResolvedValueOnce(root).mockResolvedValueOnce({ path: "src", entries: [{ path: "src/a.py", name: "a.py", kind: "file", size: 8 }] }) });
    render(<ProjectFilesPanel projectId="p-1" service={api} />);
    expect(screen.getByText("Carregando arquivos...")).toBeTruthy();
    fireEvent.click(await screen.findByRole("button", { name: /src/ }));
    expect(await screen.findByRole("button", { name: /a.py/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /README.md/ }));
    expect(await screen.findByText("Olá")).toBeTruthy();
    expect(screen.getAllByText("Somente leitura").length).toBeGreaterThan(0);
    expect(api.listDirectory).toHaveBeenNthCalledWith(2, "p-1", "src");
    expect(api.readFile).toHaveBeenCalledWith("p-1", "README.md");
  });

  it.each([["WORKSPACE_BINARY_FILE", "Arquivos binários não podem ser visualizados."], ["WORKSPACE_FILE_TOO_LARGE", "Este arquivo é muito grande para visualização."]])("shows safe %s state", async (code, message) => {
    const api = service({ readFile: vi.fn().mockRejectedValue(new ApiHttpError(400, code, "safe")) });
    render(<ProjectFilesPanel projectId="p-1" service={api} />);
    fireEvent.click(await screen.findByRole("button", { name: /README.md/ }));
    expect(await screen.findByText(message)).toBeTruthy();
  });

  it("ignores a stale root response after project change", async () => {
    let resolveOld!: (value: typeof root) => void;
    const listDirectory = vi.fn().mockImplementationOnce(() => new Promise<typeof root>((resolve) => { resolveOld = resolve; })).mockResolvedValueOnce({ path: "", entries: [] });
    const view = render(<ProjectFilesPanel key="p-1" projectId="p-1" service={service({ listDirectory })} />);
    view.rerender(<ProjectFilesPanel key="p-2" projectId="p-2" service={service({ listDirectory })} />);
    expect(await screen.findByText("Pasta vazia")).toBeTruthy();
    resolveOld(root);
    expect(screen.queryByText("README.md")).toBeNull();
  });
});
