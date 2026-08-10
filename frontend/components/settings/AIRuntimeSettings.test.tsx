// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AIRuntimeStatusDto } from "../../lib/api/dtos";
import type { AIRuntimeSettingsService } from "../../lib/services/aiRuntimeSettings";
import { AIRuntimeSettings } from "./AIRuntimeSettings";

afterEach(cleanup);

const ready: AIRuntimeStatusDto = {
  runtime_id: "codex", installed: true, authenticated: true, ready: true,
  state: "ready", version: "1.2.3", message: "Codex is ready.",
  authentication_command: null,
};
const service = (status: AIRuntimeStatusDto | Promise<AIRuntimeStatusDto>): AIRuntimeSettingsService => ({
  codexStatus: vi.fn().mockImplementation(() => Promise.resolve(status)),
});

describe("AIRuntimeSettings", () => {
  it("shows loading then ready with version", async () => {
    const pending = new Promise<AIRuntimeStatusDto>(() => undefined);
    const view = render(<AIRuntimeSettings service={service(pending)} />);
    expect(screen.getByRole("status").textContent).toContain("Verificando conexão com o Codex");
    view.unmount();
    render(<AIRuntimeSettings service={service(ready)} />);
    expect(await screen.findByText("● Pronto")).toBeTruthy();
    expect(screen.getByText("1.2.3")).toBeTruthy();
  });

  it("shows not installed and installation guidance", async () => {
    render(<AIRuntimeSettings service={service({ ...ready, installed: false, authenticated: false, ready: false, state: "not_installed", version: null })} />);
    expect(await screen.findByText("● Não instalado")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver instruções de instalação" })).toBeTruthy();
  });

  it("shows official login instruction without sensitive data", async () => {
    render(<AIRuntimeSettings service={service({ ...ready, authenticated: false, ready: false, state: "not_authenticated", authentication_command: "codex login" })} />);
    expect(await screen.findByText("● Não conectado")).toBeTruthy();
    expect(screen.getByText("codex login")).toBeTruthy();
    const content = document.body.textContent?.toLowerCase() ?? "";
    expect(content).not.toContain("access_token");
    expect(content).not.toContain("refresh_token");
    expect(content).not.toContain("cookie");
  });

  it("shows error and retries", async () => {
    const codexStatus = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(ready);
    render(<AIRuntimeSettings service={{ codexStatus }} />);
    fireEvent.click(await screen.findByRole("button", { name: "Verificar novamente" }));
    expect(await screen.findByText("● Pronto")).toBeTruthy();
    expect(codexStatus).toHaveBeenCalledTimes(2);
  });

  it("checks again from a loaded status", async () => {
    const codexStatus = vi.fn().mockResolvedValue(ready);
    render(<AIRuntimeSettings service={{ codexStatus }} />);
    fireEvent.click(await screen.findByRole("button", { name: "Verificar novamente" }));
    await screen.findByText("● Pronto");
    expect(codexStatus).toHaveBeenCalledTimes(2);
  });
});
