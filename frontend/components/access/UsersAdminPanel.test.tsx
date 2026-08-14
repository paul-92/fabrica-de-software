// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiHttpError, ApiNetworkError } from "../../lib/api/errors";
import { UsersAdminPanel } from "./UsersAdminPanel";
import { BetaUsagePanel } from "./BetaUsagePanel";

const admin = { user_id: "admin-1", organization_id: "org-1", role: "admin" as const };
const member = { user_id: "member-1", organization_id: "org-1", role: "member" as const };
const existing = { user_id: "user-1", email: "one@example.test", role: "member" as const, status: "active" as const };

afterEach(() => { cleanup(); localStorage.clear(); sessionStorage.clear(); vi.restoreAllMocks(); });

function client(overrides = {}) {
  return {
    users: vi.fn().mockResolvedValue({ items: [existing] }),
    invite: vi.fn().mockResolvedValue({ ...existing, user_id: "new" }),
    setStatus: vi.fn().mockResolvedValue({ ...existing, status: "suspended" }),
    ...overrides,
  };
}

function openForm(access = client()) {
  render(<UsersAdminPanel access={access as never} principal={admin} />);
  fireEvent.click(screen.getByRole("button", { name: "Adicionar usuário" }));
  return access;
}

function fill(email = "new@example.test", password = "temporary-password", confirmation = password) {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Senha temporária"), { target: { value: password } });
  fireEvent.change(screen.getByLabelText("Confirmar senha"), { target: { value: confirmation } });
}

function submitButton() { return within(screen.getByRole("dialog")).getByRole("button", { name: "Adicionar usuário" }); }

describe("UsersAdminPanel", () => {
  it("shows administration to admins and no affordance to members", async () => {
    const { rerender } = render(<UsersAdminPanel access={client() as never} principal={admin} />);
    expect(screen.getByRole("button", { name: "Adicionar usuário" })).toBeTruthy();
    rerender(<UsersAdminPanel access={client() as never} principal={member} />);
    expect(screen.queryByRole("button", { name: "Adicionar usuário" })).toBeNull();
  });

  it("opens an accessible form, focuses email, defaults to member and cancels with Escape", async () => {
    openForm();
    expect(screen.getByRole("dialog", { name: "Adicionar usuário" })).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBe(document.activeElement);
    expect((screen.getByLabelText("Perfil") as HTMLSelectElement).value).toBe("member");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "Adicionar usuário" })).toBe(document.activeElement));
  });

  it("validates required email, password length and confirmation", async () => {
    const access = openForm();
    fill("", "short", "short");
    fireEvent.submit(submitButton().closest("form")!);
    expect(screen.getByText("Informe o email.")).toBeTruthy();
    fill("new@example.test", "short", "short");
    fireEvent.submit(submitButton().closest("form")!);
    expect(screen.getByText(/pelo menos 12 caracteres/)).toBeTruthy();
    fill("new@example.test", "temporary-password", "different-password");
    fireEvent.submit(submitButton().closest("form")!);
    expect(screen.getByText("As senhas não coincidem.")).toBeTruthy();
    expect(access.invite).not.toHaveBeenCalled();
  });

  it("creates a member, clears password state and refreshes the list", async () => {
    const access = openForm(); fill();
    fireEvent.click(submitButton());
    expect(await screen.findByText("Usuário adicionado.")).toBeTruthy();
    expect(access.invite).toHaveBeenCalledWith("new@example.test", "temporary-password", "member");
    expect(access.users).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByDisplayValue("temporary-password")).toBeNull();
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
  });

  it("requires an explicit selection to create an admin", async () => {
    const access = openForm(); fill();
    fireEvent.change(screen.getByLabelText("Perfil"), { target: { value: "admin" } });
    fireEvent.click(submitButton());
    await waitFor(() => expect(access.invite).toHaveBeenCalledWith("new@example.test", "temporary-password", "admin"));
  });

  it.each([
    [new ApiHttpError(403, "FORBIDDEN", "internal"), "Acesso administrativo necessário."],
    [new ApiHttpError(409, "CONFLICT", "internal"), "O usuário não pôde ser criado porque já existe ou há um conflito."],
    [new ApiNetworkError("internal", new Error("offline")), "Não foi possível conectar. Tente novamente."],
  ])("maps bounded create errors without echoing internals", async (failure, expected) => {
    const access = openForm(client({ invite: vi.fn().mockRejectedValue(failure) })); fill();
    fireEvent.click(submitButton());
    expect(await screen.findByText(expected)).toBeTruthy();
    expect(screen.queryByText("internal")).toBeNull();
    expect(screen.queryByDisplayValue("temporary-password")).toBeNull();
    expect(access.invite).toHaveBeenCalledTimes(1);
  });

  it("blocks duplicate submits while the request is pending", async () => {
    let resolve!: (value: unknown) => void;
    const pending = new Promise((done) => { resolve = done; });
    const access = openForm(client({ invite: vi.fn().mockReturnValue(pending) })); fill();
    const submit = submitButton();
    fireEvent.click(submit); fireEvent.click(submit);
    expect(access.invite).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Adicionando…" }) as HTMLButtonElement).disabled).toBe(true);
    resolve(existing);
    await screen.findByText("Usuário adicionado.");
  });

  it("preserves suspension and reactivation with list refresh", async () => {
    const suspended = { ...existing, status: "suspended" as const };
    const access = client();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    access.users.mockResolvedValueOnce({ items: [existing] }).mockResolvedValueOnce({ items: [suspended] }).mockResolvedValueOnce({ items: [existing] });
    render(<UsersAdminPanel access={access as never} principal={admin} />);
    fireEvent.click(await screen.findByRole("button", { name: "Suspender" }));
    await waitFor(() => expect(access.setStatus).toHaveBeenCalledWith("user-1", "suspended"));
    fireEvent.click(await screen.findByRole("button", { name: "Reativar" }));
    await waitFor(() => expect(access.setStatus).toHaveBeenCalledWith("user-1", "active"));
  });

  it("marks the current admin and removes only its suspend action", async () => {
    const self = { ...existing, user_id: admin.user_id, role: "admin" as const };
    render(<UsersAdminPanel access={client({ users: vi.fn().mockResolvedValue({ items: [self, existing] }) }) as never} principal={admin} />);
    expect(await screen.findByText("admin · active · Você")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Suspender" })).toHaveLength(1);
  });

  it("confirms suspension and cancellation does not call the API", async () => {
    const access = client(); const confirmation = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<UsersAdminPanel access={access as never} principal={admin} />);
    fireEvent.click(await screen.findByRole("button", { name: "Suspender" }));
    expect(confirmation).toHaveBeenCalledWith("Suspender este usuário?\nEle perderá acesso até ser reativado.");
    expect(access.setStatus).not.toHaveBeenCalled();
  });

  it("maps a bypassed backend self-suspension rejection safely", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const access = client({ setStatus: vi.fn().mockRejectedValue(new ApiHttpError(409, "internal", "sensitive detail")) });
    render(<UsersAdminPanel access={access as never} principal={admin} />);
    fireEvent.click(await screen.findByRole("button", { name: "Suspender" }));
    expect(await screen.findByText("Você não pode suspender sua própria conta.")).toBeTruthy();
    expect(screen.queryByText("sensitive detail")).toBeNull();
  });

  it("keeps quota presentation independent from user administration", async () => {
    const quota = vi.fn().mockResolvedValue({ quota: { enabled: true, call_limit: 10, token_limit: 100, period: "monthly" }, usage: { calls: 2, known_total_tokens: 20, calls_with_unknown_usage: 0, period_started_at: "x", period_ends_at: "y" } });
    render(<BetaUsagePanel access={{ quota } as never} principal={admin} />);
    expect(await screen.findByText("2 / 10 chamadas; 20 / 100 tokens conhecidos.")).toBeTruthy();
  });
});
