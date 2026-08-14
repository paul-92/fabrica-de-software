"use client";

import type { FormEvent, PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import { createPlatformClients } from "../../lib/api";
import type { AccessClient, AccessPrincipal } from "../../lib/services/access";
import { BetaUsagePanel } from "./BetaUsagePanel";
import { UsersAdminPanel } from "./UsersAdminPanel";

type Props = PropsWithChildren<{ client?: AccessClient }>;

export function AccessGate({ client, children }: Props) {
  const [access] = useState<AccessClient | null>(() => client ?? (typeof window === "undefined" ? null : createPlatformClients().access));
  const [principal, setPrincipal] = useState<AccessPrincipal | null | undefined>(undefined);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!access) return; let active = true; access.session().then(
    (value) => { if (active) setPrincipal(value); },
    () => { if (active) setPrincipal(null); },
  ); return () => { active = false; }; }, [access]);
  useEffect(() => { const unauthorized = () => setPrincipal(null); window.addEventListener("asep:unauthorized", unauthorized); return () => window.removeEventListener("asep:unauthorized", unauthorized); }, []);

  if (principal === undefined) return <main className="access-screen"><p role="status">Reconstruindo sessão…</p></main>;

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(false);
    try { if (!access) return; setPrincipal(await access.login(email, password)); setPassword(""); }
    catch { setError(true); }
    finally { setBusy(false); }
  }

  async function logout() { await access?.logout().catch(() => undefined); setPrincipal(null); }

  if (!principal) return <main className="access-screen"><section className="card access-card"><h1>Acesso à ASEP</h1><p>Private Beta por convite.</p><form className="engineering-form" onSubmit={login}><label>Email<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Senha<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error ? <p role="alert">Não foi possível autenticar.</p> : null}<button className="button button--primary" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button></form></section></main>;

  return <><div className="access-session" aria-label="Sessão atual"><span>{principal.user_id} · {principal.role}</span><BetaUsagePanel access={access!} principal={principal}/>{principal.role === "admin" ? <UsersAdminPanel access={access!} principal={principal} /> : null}<button type="button" onClick={logout}>Sair</button></div>{children}</>;
}
