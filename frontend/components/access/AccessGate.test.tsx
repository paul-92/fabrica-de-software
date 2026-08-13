// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccessGate } from "./AccessGate";

afterEach(() => { cleanup(); localStorage.clear(); });

function client(overrides = {}) {
  return { session: vi.fn().mockRejectedValue(new Error("401")), login: vi.fn(), logout: vi.fn().mockResolvedValue(undefined), ...overrides } as never;
}

describe("AccessGate", () => {
  it("reconstructs an authenticated server session and logs out", async () => {
    const access = client({ session: vi.fn().mockResolvedValue({ user_id: "u-1", organization_id: "o-1", role: "admin" }), logout: vi.fn().mockResolvedValue(undefined) });
    render(<AccessGate client={access}><p>Private content</p></AccessGate>);
    expect(await screen.findByText("Private content")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("heading", { name: "Acesso à ASEP" })).toBeTruthy();
  });

  it("logs in without persisting a token in localStorage", async () => {
    const access = client({ login: vi.fn().mockResolvedValue({ user_id: "u-1", organization_id: "o-1", role: "member" }) });
    render(<AccessGate client={access}><p>Private content</p></AccessGate>);
    await screen.findByRole("heading", { name: "Acesso à ASEP" });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "member@example.test" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "private-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Private content")).toBeTruthy();
    expect(localStorage.length).toBe(0);
  });

  it("returns to access on a later 401", async () => {
    const access = client({ session: vi.fn().mockResolvedValue({ user_id: "u-1", organization_id: "o-1", role: "member" }) });
    render(<AccessGate client={access}><p>Private content</p></AccessGate>);
    await screen.findByText("Private content");
    window.dispatchEvent(new Event("asep:unauthorized"));
    expect(await screen.findByRole("heading", { name: "Acesso à ASEP" })).toBeTruthy();
  });
});
