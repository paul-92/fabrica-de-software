"use client";

import type { FormEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { ApiHttpError, ApiNetworkError } from "../../lib/api/errors";
import type { AccessClient, AccessPrincipal, AccessUser } from "../../lib/services/access";

type Role = "admin" | "member";

function createError(error: unknown): string {
  if (error instanceof ApiHttpError && error.status === 403) return "Acesso administrativo necessário.";
  if (error instanceof ApiHttpError && error.status === 409) return "O usuário não pôde ser criado porque já existe ou há um conflito.";
  if (error instanceof ApiHttpError && error.status === 422) return "Revise os dados informados.";
  if (error instanceof ApiNetworkError) return "Não foi possível conectar. Tente novamente.";
  return "Não foi possível adicionar o usuário. Tente novamente.";
}

function statusError(error: unknown): string {
  if (error instanceof ApiHttpError && error.status === 409) {
    const body = error.responseBody as { detail?: unknown } | undefined;
    if (body?.detail === "At least one active administrator is required.") return "A organização precisa manter ao menos um administrador ativo.";
    return "Você não pode suspender sua própria conta.";
  }
  return "Não foi possível atualizar o status do usuário. Tente novamente.";
}

export function UsersAdminPanel({ access, principal }: { access: AccessClient; principal: AccessPrincipal }) {
  const [users, setUsers] = useState<AccessUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const openButton = useRef<HTMLButtonElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);

  async function refresh() { setUsers((await access.users()).items); }

  useEffect(() => {
    let active = true;
    if (principal.role !== "admin") return () => { active = false; };
    if (typeof access.users !== "function") return () => { active = false; };
    access.users().then(
      (value) => { if (active) setUsers(value.items); },
      () => { if (active) setError("Não foi possível carregar os usuários. Tente novamente."); },
    ).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [access, principal.role]);

  useEffect(() => {
    if (!open) return;
    emailInput.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || busy) return;
      setPassword(""); setConfirmation(""); setEmail(""); setRole("member"); setError(""); setOpen(false);
      queueMicrotask(() => openButton.current?.focus());
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, busy]);

  if (principal.role !== "admin") return null;

  function clearSensitiveFields() { setPassword(""); setConfirmation(""); }
  function close() {
    clearSensitiveFields(); setEmail(""); setRole("member"); setError(""); setOpen(false);
    queueMicrotask(() => openButton.current?.focus());
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(""); setMessage("");
    if (!email.trim()) { setError("Informe o email."); return; }
    if (password.length < 12) { setError("A senha temporária deve conter pelo menos 12 caracteres."); return; }
    if (password !== confirmation) { setError("As senhas não coincidem."); return; }
    setBusy(true);
    try {
      await access.invite(email.trim(), password, role);
      clearSensitiveFields(); await refresh(); setMessage("Usuário adicionado.");
      setEmail(""); setRole("member"); setOpen(false);
      queueMicrotask(() => openButton.current?.focus());
    } catch (requestError) { setError(createError(requestError)); }
    finally { clearSensitiveFields(); setBusy(false); }
  }

  async function toggleStatus(user: AccessUser) {
    setError("");
    const nextStatus = user.status === "active" ? "suspended" : "active";
    if (nextStatus === "suspended" && !window.confirm("Suspender este usuário?\nEle perderá acesso até ser reativado.")) return;
    try { await access.setStatus(user.user_id, nextStatus); await refresh(); }
    catch (requestError) { setError(statusError(requestError)); }
  }

  const activeAdminCount = users.filter((user) => user.role === "admin" && user.status === "active").length;

  return <details className="users-admin"><summary>Usuários</summary>
    <div className="users-admin__header"><p>Gerencie os usuários do Private Beta.</p><button ref={openButton} className="button button--primary" type="button" onClick={() => { setError(""); setOpen(true); }}>Adicionar usuário</button></div>
    <div aria-live="polite">{message ? <p className="users-admin__success">{message}</p> : null}{error && !open ? <p role="alert" className="engineering-form__error">{error}</p> : null}</div>
    {loading ? <p role="status">Carregando usuários…</p> : <ul className="users-admin__list">{users.map((user) => { const current = user.user_id === principal.user_id; const lastActiveAdmin = user.role === "admin" && user.status === "active" && activeAdminCount <= 1; const suspensionBlocked = user.status === "active" && (current || lastActiveAdmin); return <li key={user.user_id}><span><strong>{user.email}</strong><small>{user.role} · {user.status}{current ? " · Você" : ""}</small>{lastActiveAdmin ? <small>A organização precisa manter ao menos um administrador ativo.</small> : null}</span>{suspensionBlocked ? null : <button type="button" disabled={busy} onClick={() => void toggleStatus(user)}>{user.status === "active" ? "Suspender" : "Reativar"}</button>}</li>; })}</ul>}
    {open ? <div className="users-admin__backdrop" role="presentation"><section className="users-admin__dialog" role="dialog" aria-modal="true" aria-labelledby="add-user-title"><h2 id="add-user-title">Adicionar usuário</h2><form className="engineering-form" onSubmit={submit}>
      <label>Email<input ref={emailInput} type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} required /></label>
      <label>Perfil<select value={role} onChange={(event) => setRole(event.target.value as Role)} disabled={busy}><option value="member">Member</option><option value="admin">Admin</option></select></label>
      <label>Senha temporária<input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} minLength={12} required /></label>
      <label>Confirmar senha<input type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} disabled={busy} minLength={12} required /></label>
      <div aria-live="assertive">{error ? <p role="alert" className="engineering-form__error">{error}</p> : null}</div>
      <div className="users-admin__actions"><button className="button button--secondary" type="button" onClick={close} disabled={busy}>Cancelar</button><button className="button button--primary" type="submit" disabled={busy}>{busy ? "Adicionando…" : "Adicionar usuário"}</button></div>
    </form></section></div> : null}
  </details>;
}
