"use client";

import { useEffect, useMemo, useState } from "react";
import type { AIRuntimeStatusDto } from "../../lib/api/dtos";
import {
  createAIRuntimeSettingsService,
  type AIRuntimeSettingsService,
} from "../../lib/services/aiRuntimeSettings";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";
import { StatusBadge } from "../StatusBadge";

export function AIRuntimeSettings({ service }: { service?: AIRuntimeSettingsService }) {
  const api = useMemo(() => service ?? createAIRuntimeSettingsService(), [service]);
  const [status, setStatus] = useState<AIRuntimeStatusDto | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    api.codexStatus().then(
      (value) => { if (active) { setStatus(value); setFailed(false); } },
      () => { if (active) { setStatus(null); setFailed(true); } },
    );
    return () => { active = false; };
  }, [api, attempt]);

  const retry = () => { setStatus(null); setFailed(false); setAttempt((value) => value + 1); };

  return <div className="page-stack">
    <PageHeader eyebrow="Configurações" title="Assistente de IA" description="Conecte assistentes compatíveis sem compartilhar credenciais com a plataforma." />
    {!status && !failed ? <div role="status" className="executions-skeleton"><span className="sr-only">Verificando conexão com o Codex</span></div> : null}
    {failed ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Status do Codex indisponível</h2><p>Verifique se a API está em execução e tente novamente.</p><Button onClick={retry}>Verificar novamente</Button></div> : null}
    {status ? <Card eyebrow="Assistente de IA" title="Codex">
      <dl className="runtime-status">
        <div><dt>Instalação</dt><dd>{status.installed ? <StatusBadge status="success">● Instalado</StatusBadge> : <StatusBadge status="danger">● Não instalado</StatusBadge>}</dd></div>
        <div><dt>Versão</dt><dd>{status.version ?? "Indisponível"}</dd></div>
        <div><dt>Autenticação</dt><dd>{status.authenticated ? <StatusBadge status="success">● Conectado</StatusBadge> : <StatusBadge status="warning">● Não conectado</StatusBadge>}</dd></div>
        <div><dt>Status</dt><dd>{status.ready ? <StatusBadge status="success">● Pronto</StatusBadge> : <StatusBadge status="warning">● Indisponível</StatusBadge>}</dd></div>
      </dl>
      {!status.installed ? <div className="runtime-guidance"><p>O Codex é necessário para usar este assistente.</p><a href="https://developers.openai.com/codex/cli/" target="_blank" rel="noreferrer">Ver instruções de instalação</a></div> : null}
      {status.state === "not_authenticated" ? <div className="runtime-guidance"><p>Conecte sua conta do Codex pelo cliente oficial:</p><code>{status.authentication_command ?? "codex login"}</code><p>A ASEP nunca recebe sua senha ou tokens.</p></div> : null}
      <Button variant="secondary" onClick={retry}>Verificar novamente</Button>
    </Card> : null}
  </div>;
}
