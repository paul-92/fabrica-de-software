"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto, ProjectExecutionDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind } from "../../lib/api/dtos";
import { createProjectRuntimeWorkspaceService, type ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";
import { formatExecutionMode, formatExecutionStatus, formatMemoryKind, formatWorkspaceChange } from "../../lib/presentation";

type Props = { projectId: string; projectName: string; workspacePath: string; service?: ProjectRuntimeWorkspaceService };

export function ProjectRuntimePanel({ projectId, projectName, workspacePath, service }: Props) {
  const api = useMemo(() => service ?? createProjectRuntimeWorkspaceService(), [service]);
  const [status, setStatus] = useState<AIRuntimeStatusDto | null>(null);
  const [statusAttempt, setStatusAttempt] = useState(0);
  const [statusFailed, setStatusFailed] = useState(false);
  const [sessions, setSessions] = useState<readonly ProjectSessionDto[] | null>(null);
  const [sessionsLoadError, setSessionsLoadError] = useState(false);
  const [sessionsAttempt, setSessionsAttempt] = useState(0);
  const [selectedSession, setSelectedSession] = useState<ProjectSessionDto | null>(null);
  const [sessionTitle, setSessionTitle] = useState("");
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [history, setHistory] = useState<readonly ProjectExecutionDto[] | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<ProjectExecutionDto | null>(null);
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState<AIRuntimeExecutionMode>("read_only");
  const [confirmingWrite, setConfirmingWrite] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectAIRuntimeExecutionDto | null>(null);
  const [memory, setMemory] = useState<readonly SessionMemoryDto[] | null>(null);
  const [memoryKind, setMemoryKind] = useState<SessionMemoryKind>("fact");
  const [memoryContent, setMemoryContent] = useState("");
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [addingMemory, setAddingMemory] = useState(false);

  useEffect(() => {
    let active = true;
    api.status().then((value) => { if (active) { setStatus(value); setStatusFailed(false); } }, () => { if (active) { setStatus(null); setStatusFailed(true); } });
    return () => { active = false; };
  }, [api, statusAttempt]);

  useEffect(() => {
    let active = true;
    api.listSessions(projectId).then((items) => { if (active) { setSessions(items); setSessionsLoadError(false); setHistory(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setResult(null); setSelectedSession(items[0] ?? null); } }, () => { if (active) { setSessions([]); setSessionsLoadError(true); } });
    return () => { active = false; };
  }, [api, projectId, sessionsAttempt]);

  useEffect(() => {
    if (!selectedSession) return;
    let active = true;
    api.listExecutions(projectId, selectedSession.session_id).then((items) => { if (active) setHistory(items); }, () => { if (active) setHistory([]); });
    return () => { active = false; };
  }, [api, projectId, selectedSession]);

  useEffect(() => {
    if (!selectedSession) return;
    let active = true;
    api.listMemory(projectId, selectedSession.session_id).then(
      (items) => { if (active) { setMemory(items); setMemoryError(null); } },
      () => { if (active) { setMemory([]); setMemoryError("Não foi possível carregar a memória da sessão."); } },
    );
    return () => { active = false; };
  }, [api, projectId, selectedSession]);

  async function addMemory(event: FormEvent) {
    event.preventDefault(); if (!selectedSession || addingMemory) return;
    const kind = memoryKind;
    const content = memoryContent.trim();
    if (!content) { setMemoryError("Informe o conteúdo da memória."); return; }
    setAddingMemory(true); setMemoryError(null);
    try {
      const added = await api.addMemory(projectId, selectedSession.session_id, kind, content);
      setMemory((items) => [added, ...(items ?? []).filter((item) => item.memory_id !== added.memory_id)]);
      setMemoryContent("");
    } catch { setMemoryError("Não foi possível adicionar a memória."); }
    finally { setAddingMemory(false); }
  }

  async function createSession(event: FormEvent) {
    event.preventDefault(); if (creatingSession) return;
    if (!sessionTitle.trim()) { setSessionError("Informe o nome da sessão."); return; }
    setCreatingSession(true); setSessionError(null);
    try {
      const created = await api.createSession(projectId, sessionTitle.trim());
      setSessions((items) => [created, ...(items ?? [])]);
      setHistory(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setResult(null); setSelectedSession(created); setSessionTitle("");
    } catch { setSessionError("Não foi possível criar a sessão. Tente novamente."); }
    finally { setCreatingSession(false); }
  }

  async function run() {
    if (submitting || !selectedSession) return;
    setSubmitting(true); setError(null); setResult(null); setConfirmingWrite(false);
    try {
      const completed = await api.execute(projectId, selectedSession.session_id, instruction.trim(), mode);
      setResult(completed);
      setHistory(await api.listExecutions(projectId, selectedSession.session_id));
      const refreshedMemory = await api.listMemory(projectId, selectedSession.session_id).catch(() => null);
      if (refreshedMemory !== null) setMemory(refreshedMemory);
    } catch {
      setError("O Codex não conseguiu concluir a tarefa. A execução com falha permanece no histórico.");
      setHistory(await api.listExecutions(projectId, selectedSession.session_id).catch(() => []));
    } finally { setSubmitting(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); if (submitting) return;
    if (!instruction.trim()) { setError("Descreva a tarefa antes de executar."); return; }
    if (mode === "workspace_write") { setConfirmingWrite(true); return; }
    await run();
  }

  const runtimeReady = status?.ready === true || status?.state === "ready";
  const runtimeLabel = statusFailed ? "Indisponível" : status === null ? "Carregando status do Codex..." : runtimeReady ? "Pronto" : status.state === "not_installed" ? "Não instalado" : status.state === "error" ? "Indisponível" : "Não conectado";

  return <div className="page-stack">
    <Card title="Sessões" eyebrow="Trabalho do projeto"><form className="engineering-form" onSubmit={createSession}><label>Nome da sessão<input placeholder="Ex.: Implementação da API de clientes" value={sessionTitle} onChange={(event) => setSessionTitle(event.target.value)} disabled={creatingSession} /></label>{sessionError ? <p role="alert" className="engineering-form__error">{sessionError}</p> : null}<Button type="submit" disabled={creatingSession}>{creatingSession ? "Criando…" : "Nova sessão"}</Button></form>{sessions === null ? <p role="status">Carregando sessões...</p> : sessionsLoadError ? <div role="alert"><p>Não foi possível carregar as sessões.</p><Button onClick={() => { setSessions(null); setSessionsAttempt((value) => value + 1); }}>Tentar novamente</Button></div> : sessions.length === 0 ? <p>Nenhuma sessão ainda.</p> : <ul>{sessions.map((session) => <li key={session.session_id}><button type="button" onClick={() => { setHistory(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setResult(null); setError(null); setConfirmingWrite(false); setSelectedSession(session); }} aria-pressed={selectedSession?.session_id === session.session_id}>{session.title}</button></li>)}</ul>}</Card>
    {selectedSession ? <Card title={selectedSession.title} eyebrow="Assistente de IA">
      <div className="status-row"><StatusBadge status={runtimeReady ? "success" : "warning"}>{`● ${runtimeLabel}`}</StatusBadge><StatusBadge>{mode === "read_only" ? "Sessão somente leitura" : "Alterações permitidas"}</StatusBadge></div>
      {statusFailed ? <Button onClick={() => { setStatus(null); setStatusFailed(false); setStatusAttempt((value) => value + 1); }}>Verificar novamente</Button> : status === null ? null : !runtimeReady ? <p><Link href="/settings/ai">Configurar assistente de IA</Link></p> : <form className="engineering-form" onSubmit={submit}><fieldset className="mode-selector" disabled={submitting}><legend>Modo de execução</legend><label><input type="radio" name="execution-mode" value="read_only" checked={mode === "read_only"} onChange={() => { setMode("read_only"); setConfirmingWrite(false); }} /> Somente leitura</label><label><input type="radio" name="execution-mode" value="workspace_write" checked={mode === "workspace_write"} onChange={() => setMode("workspace_write")} /> Permitir alterações no projeto</label></fieldset><label>Tarefa<textarea placeholder="Descreva o que você quer que o Codex faça neste projeto..." value={instruction} onChange={(event) => setInstruction(event.target.value)} disabled={submitting} /></label>{error ? <p role="alert" className="engineering-form__error">{error}</p> : null}<Button type="submit" disabled={submitting}>{submitting ? "Executando — a pasta pode estar sendo alterada…" : "Executar com Codex"}</Button></form>}
      {confirmingWrite ? <section role="alertdialog" aria-labelledby="write-confirmation-title"><h3 id="write-confirmation-title">Confirmar alterações no projeto</h3><p>O Codex pode criar, modificar ou excluir arquivos nesta pasta. As alterações não são desfeitas automaticamente.</p><dl><div><dt>Projeto</dt><dd>{projectName}</dd></div><div><dt>Pasta</dt><dd>{workspacePath}</dd></div><div><dt>Modo</dt><dd>{formatExecutionMode("workspace_write")}</dd></div></dl><Button onClick={() => setConfirmingWrite(false)} disabled={submitting}>Cancelar</Button><Button onClick={run} disabled={submitting}>Confirmar e executar</Button></section> : null}
      {result ? <div className="runtime-result"><h3>Resultado do Codex</h3><pre>{result.output}</pre><p>Modo: {formatExecutionMode(result.execution_mode)}</p><ContextUsage count={result.context_entry_count} truncated={result.context_truncated} charCount={result.context_char_count} omittedCount={result.context_omitted_execution_count} /><MemoryUsage count={result.memory_entry_count} charCount={result.memory_char_count} truncated={result.memory_truncated} /><h4>Alterações no projeto</h4>{result.changes.length === 0 ? <p>Nenhuma alteração detectada no projeto.</p> : <ChangeList changes={result.changes} />}</div> : null}
    </Card> : null}
    {selectedSession ? <Card title="Memória da sessão" eyebrow="Informações duráveis"><form className="engineering-form" onSubmit={addMemory}><label>Tipo<select value={memoryKind} onChange={(event) => setMemoryKind(event.target.value as SessionMemoryKind)} disabled={addingMemory}><option value="fact">Fato</option><option value="decision">Decisão</option><option value="constraint">Restrição</option><option value="artifact">Artefato</option><option value="goal">Objetivo</option></select></label><label>Memória<input placeholder="Registre uma informação importante desta sessão" value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} disabled={addingMemory} /></label>{memoryError ? <p role="alert">{memoryError}</p> : null}<Button type="submit" disabled={addingMemory}>{addingMemory ? "Adicionando…" : "Adicionar memória"}</Button></form>{memory === null ? <p role="status">Carregando memória...</p> : memory.length === 0 ? <p>Nenhuma memória nesta sessão.</p> : <ul>{memory.map((entry) => <li key={entry.memory_id}><strong>{formatMemoryKind(entry.kind)}</strong> {entry.content}<small>{entry.source_execution_id ? `Execução ${entry.source_execution_id}` : "Manual"}</small></li>)}</ul>}</Card> : null}
    {selectedSession ? <Card title="Histórico" eyebrow="Execuções">{history === null ? <p role="status">Carregando histórico...</p> : history.length === 0 ? <p>Nenhuma execução ainda.</p> : <ul>{history.map((execution) => <li key={execution.execution_id}><button type="button" onClick={() => setSelectedExecution(execution)}><strong>{formatExecutionStatus(execution.status)}</strong> · {execution.runtime_id} · {formatExecutionMode(execution.execution_mode)}<br />{execution.instruction}<br />{execution.changes.length} arquivos alterados{execution.usage?.input_units != null ? ` · ${execution.usage.input_units} tokens de entrada` : ""}{execution.usage?.output_units != null ? ` · ${execution.usage.output_units} tokens de saída` : ""}</button></li>)}</ul>}</Card> : null}
    {selectedExecution ? <Card title="Detalhes da execução" eyebrow={formatExecutionStatus(selectedExecution.status)}><p><strong>Tarefa</strong><br />{selectedExecution.instruction}</p><p><strong>Resultado</strong><br />{selectedExecution.output ?? "Nenhum resultado disponível."}</p><ContextUsage count={selectedExecution.context_entry_count} truncated={selectedExecution.context_truncated} charCount={selectedExecution.context_char_count} omittedCount={selectedExecution.context_omitted_execution_count} /><MemoryUsage count={selectedExecution.memory_entry_count} charCount={selectedExecution.memory_char_count} truncated={selectedExecution.memory_truncated} /><dl className="execution-facts"><div><dt>Assistente</dt><dd>{selectedExecution.runtime_id}</dd></div><div><dt>Modelo</dt><dd>{selectedExecution.model ?? "Desconhecido"}</dd></div><div><dt>Modo</dt><dd>{formatExecutionMode(selectedExecution.execution_mode)}</dd></div><div><dt>Status</dt><dd>{formatExecutionStatus(selectedExecution.status)}</dd></div>{selectedExecution.error_code ? <div><dt>Erro</dt><dd>{selectedExecution.error_code}</dd></div> : null}</dl><h4>Alterações no projeto</h4>{selectedExecution.changes.length ? <ChangeList changes={selectedExecution.changes} /> : <p>Nenhuma alteração detectada no projeto.</p>}</Card> : null}
  </div>;
}

function ContextUsage({ count, truncated, charCount, omittedCount }: { count: number; truncated: boolean; charCount: number; omittedCount: number }) {
  if (count === 0) return null;
  return <p>Usando contexto de {count} {count === 1 ? "execução anterior" : "execuções anteriores"}. Tamanho do contexto: {formatContextChars(charCount)}.{omittedCount > 0 ? ` ${omittedCount} ${omittedCount === 1 ? "execução anterior omitida" : "execuções anteriores omitidas"}.` : ""}{truncated ? " O contexto recente foi compactado." : ""}</p>;
}

function formatContextChars(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} mil caracteres` : `${value} caracteres`;
}

function MemoryUsage({ count, charCount, truncated }: { count: number; charCount: number; truncated: boolean }) {
  if (count === 0) return null;
  return <p>Usando {count} {count === 1 ? "memória da sessão" : "memórias da sessão"} ({formatContextChars(charCount)}).{truncated ? " A memória da sessão foi limitada." : ""}</p>;
}

function ChangeList({ changes }: { changes: ProjectAIRuntimeExecutionDto["changes"] }) {
  return <ul>{changes.map((change) => <li key={`${change.change_type}:${change.path}`}><strong>{formatWorkspaceChange(change.change_type)}</strong> {change.path}</li>)}</ul>;
}
