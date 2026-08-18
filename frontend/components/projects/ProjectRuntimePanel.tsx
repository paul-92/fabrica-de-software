"use client";

import Link from "next/link";
import { FormEvent, useEffect, useEffectEvent, useMemo, useState } from "react";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto, ProjectEngineeringPreparationDto, ProjectExecutionDto, ProjectLifecycleDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind } from "../../lib/api/dtos";
import { createProjectRuntimeWorkspaceService, type ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";
import { formatExecutionMode, formatExecutionStatus, formatMemoryKind } from "../../lib/presentation";
import { ProjectExecutionEvidence } from "./ProjectExecutionEvidence";
import type { AIUsageResponseDto } from "../../lib/api/dtos";
import { ApiHttpError, ApiNetworkError, ApiResponseError, ApiTimeoutError } from "../../lib/api/errors";
import { ProjectLifecycle } from "./ProjectLifecycle";

type Props = { projectId: string; projectName: string; workspaceLabel: string; service?: ProjectRuntimeWorkspaceService; initialSessionId?: string; initialExecutionId?: string; onNavigate?: (sessionId: string, executionId?: string) => void };

export function ProjectRuntimePanel({ projectId, projectName, workspaceLabel, service, initialSessionId, initialExecutionId, onNavigate }: Props) {
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
  const [lifecycle, setLifecycle] = useState<ProjectLifecycleDto|null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(true);
  const [lifecycleError, setLifecycleError] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<ProjectExecutionDto | null>(null);
  const [executionLoadError, setExecutionLoadError] = useState<string | null>(null);
  const [executionAttempt, setExecutionAttempt] = useState(0);
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState<AIRuntimeExecutionMode>("read_only");
  const [confirmingWrite, setConfirmingWrite] = useState(false);
  const [preparation, setPreparation] = useState<ProjectEngineeringPreparationDto | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyRefreshError, setHistoryRefreshError] = useState<string | null>(null);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectAIRuntimeExecutionDto | ProjectExecutionDto | null>(null);
  const [memory, setMemory] = useState<readonly SessionMemoryDto[] | null>(null);
  const [memoryKind, setMemoryKind] = useState<SessionMemoryKind>("fact");
  const [memoryContent, setMemoryContent] = useState("");
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [addingMemory, setAddingMemory] = useState(false);

  useEffect(() => {
    let active=true;
    if (!api.getLifecycle) return;
    api.getLifecycle(projectId).then(value=>{if(active){setLifecycle(value);setLifecycleError(false)}},()=>{if(active)setLifecycleError(true)}).finally(()=>{if(active)setLifecycleLoading(false)});
    return()=>{active=false};
  },[api,projectId,result,preparation]);

  useEffect(() => {
    let active = true;
    api.status().then((value) => { if (active) { setStatus(value); setStatusFailed(false); } }, () => { if (active) { setStatus(null); setStatusFailed(true); } });
    return () => { active = false; };
  }, [api, statusAttempt]);

  const applySessions = useEffectEvent((items: readonly ProjectSessionDto[]) => {
    setSessions(items); setSessionsLoadError(false);
    const requested = initialSessionId
      ? items.find((item) => item.session_id === initialSessionId)
      : items.find((item) => (
        item.project_id === selectedSession?.project_id
        && item.session_id === selectedSession?.session_id
      )) ?? items[0];
    setExecutionLoadError(initialSessionId && !requested ? "A sessão informada pela URL não foi encontrada." : null);
    if (
      requested?.project_id === selectedSession?.project_id
      && requested?.session_id === selectedSession?.session_id
    ) return;
    setHistory(null); setHistoryRefreshError(null); setNavigationError(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setResult(null); setSelectedSession(requested ?? null);
  });
  useEffect(() => {
    let active = true;
    api.listSessions(projectId).then((items) => { if (active) applySessions(items); }, () => { if (active) { setSessions([]); setSessionsLoadError(true); } });
    return () => { active = false; };
  }, [api, projectId, sessionsAttempt, initialSessionId]);

  useEffect(() => {
    if (!selectedSession || !initialExecutionId) return;
    let active = true;
    api.getExecution(projectId, initialExecutionId).then(
      (execution) => {
        if (!active) return;
        if (execution.session_id !== selectedSession.session_id || execution.project_id !== projectId) {
          setSelectedExecution(null); setExecutionLoadError("A execução não pertence ao contexto informado."); return;
        }
        setSelectedExecution(execution); setExecutionLoadError(null);
      },
      () => { if (active) { setSelectedExecution(null); setExecutionLoadError("A execução informada pela URL não foi encontrada."); } },
    );
    return () => { active = false; };
  }, [api, projectId, selectedSession, initialExecutionId, executionAttempt]);

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
      setHistory(null); setHistoryRefreshError(null); setNavigationError(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setResult(null); setPreparation(null); setSelectedSession(created); setSessionTitle("");
      onNavigate?.(created.session_id);
    } catch { setSessionError("Não foi possível criar a sessão. Tente novamente."); }
    finally { setCreatingSession(false); }
  }

  async function run() {
    if (submitting || !selectedSession) return;
    setSubmitting(true); setError(null); setConfirmingWrite(false); setHistoryRefreshError(null); setNavigationError(null);
    let completed: ProjectAIRuntimeExecutionDto;
    try {
      completed = preparation
        ? await api.approve(projectId, preparation.execution_id, selectedSession.session_id, preparation.instruction)
        : await api.execute(projectId, selectedSession.session_id, instruction.trim(), mode);
    } catch (executionError) {
      let reconciledFailure = false;
      if (preparation) {
        try {
          const reconciled = await api.getExecution(projectId, preparation.execution_id);
          if (reconciled.status === "succeeded") {
            setError(null); setResult(reconciled); setPreparation(null);
            try {
              onNavigate?.(selectedSession.session_id, reconciled.execution_id);
            } catch {
              setNavigationError("A execução foi concluída, mas a navegação não pôde ser atualizada.");
            }
            try {
              setHistory(await api.listExecutions(projectId, selectedSession.session_id));
            } catch {
              setHistoryRefreshError("A execução foi concluída, mas o histórico não pôde ser atualizado.");
            }
            try {
              setMemory(await api.listMemory(projectId, selectedSession.session_id));
              setMemoryError(null);
            } catch {
              setMemoryError("A execução foi concluída, mas a memória da sessão não pôde ser atualizada.");
            }
            setSubmitting(false);
            return;
          }
          if (reconciled.status === "failed") {
            reconciledFailure = true;
            setResult(null);
            setError("O Codex não conseguiu concluir a tarefa. A execução com falha permanece no histórico.");
          } else {
            setError(uncertainExecutionMessage);
          }
        } catch {
          setError(uncertainExecutionMessage);
        }
      } else {
        setError(executionErrorMessage(executionError));
        if (isConfirmedExecutionFailure(executionError)) setResult(null);
      }
      try {
        setHistory(await api.listExecutions(projectId, selectedSession.session_id));
      } catch {
        setHistoryRefreshError(reconciledFailure
          ? "A execução falhou e o histórico não pôde ser atualizado."
          : "O resultado da execução é incerto e o histórico não pôde ser atualizado.");
      }
      setSubmitting(false);
      return;
    }

    setResult(completed);
    setPreparation(null);
    try {
      onNavigate?.(selectedSession.session_id, completed.execution_id);
    } catch {
      setNavigationError("A execução foi concluída, mas a navegação não pôde ser atualizada.");
    }
    try {
      setHistory(await api.listExecutions(projectId, selectedSession.session_id));
    } catch {
      setHistoryRefreshError("A execução foi concluída, mas o histórico não pôde ser atualizado.");
    }
    try {
      setMemory(await api.listMemory(projectId, selectedSession.session_id));
      setMemoryError(null);
    } catch {
      setMemoryError("A execução foi concluída, mas a memória da sessão não pôde ser atualizada.");
    }
    setSubmitting(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); if (submitting) return;
    if (!instruction.trim()) { setError("Descreva a tarefa antes de executar."); return; }
    if (mode === "read_only" && requiresWorkspaceWrite(instruction)) {
      setError("Esta etapa requer alterações no projeto. Ative 'Permitir alterações no projeto' para preparar a implementação.");
      return;
    }
    if (mode === "workspace_write") {
      setSubmitting(true); setError(null);
      try {
        setPreparation(await api.prepare(projectId, selectedSession!.session_id, instruction.trim()));
        setConfirmingWrite(true);
      } catch (preparationError) {
        setError(executionErrorMessage(
          preparationError,
          "Não foi possível preparar o plano de engenharia.",
        ));
        if (isConfirmedExecutionFailure(preparationError)) setResult(null);
      }
      finally { setSubmitting(false); }
      return;
    }
    await run();
  }

  async function cancelPreparation() {
    if (!preparation || !selectedSession || submitting) return;
    setSubmitting(true); setError(null);
    try {
      await api.cancel(projectId, preparation.execution_id, selectedSession.session_id, preparation.instruction);
      setPreparation(null); setConfirmingWrite(false);
      setHistory(await api.listExecutions(projectId, selectedSession.session_id));
    } catch { setError("Não foi possível cancelar a preparação."); }
    finally { setSubmitting(false); }
  }

  const runtimeReady = status?.ready === true || status?.state === "ready";
  const runtimeLabel = statusFailed ? "Indisponível" : status === null ? "Carregando status do Codex..." : runtimeReady ? "Pronto" : status.state === "not_installed" ? "Não instalado" : status.state === "error" ? "Indisponível" : "Não conectado";
  const visibleSelectedExecution = initialExecutionId && selectedExecution?.execution_id !== initialExecutionId
    ? null
    : selectedExecution;

  return <div className="page-stack">
    <Card title="Ciclo de vida" eyebrow="Progresso estruturado"><ProjectLifecycle projectName={projectName} state={lifecycle} loading={lifecycleLoading} error={lifecycleError} /></Card>
    <Card title="Sessões" eyebrow="Trabalho do projeto"><form className="engineering-form" onSubmit={createSession}><label>Nome da sessão<input placeholder="Ex.: Implementação da API de clientes" value={sessionTitle} onChange={(event) => setSessionTitle(event.target.value)} disabled={creatingSession} /></label>{sessionError ? <p role="alert" className="engineering-form__error">{sessionError}</p> : null}<Button type="submit" disabled={creatingSession}>{creatingSession ? "Criando…" : "Nova sessão"}</Button></form>{sessions === null ? <p role="status">Carregando sessões...</p> : sessionsLoadError ? <div role="alert"><p>Não foi possível carregar as sessões.</p><Button onClick={() => { setSessions(null); setSessionsAttempt((value) => value + 1); }}>Tentar novamente</Button></div> : sessions.length === 0 ? <p>Nenhuma sessão ainda.</p> : <ul className="project-runtime-selection-list">{sessions.map((session) => <li key={session.session_id}><button type="button" onClick={() => { setHistory(null); setHistoryRefreshError(null); setNavigationError(null); setMemory(null); setMemoryError(null); setMemoryContent(""); setSelectedExecution(null); setExecutionLoadError(null); setResult(null); setError(null); setConfirmingWrite(false); setSelectedSession(session); onNavigate?.(session.session_id); }} aria-pressed={selectedSession?.session_id === session.session_id}>{session.title}</button></li>)}</ul>}</Card>
    {selectedSession ? <Card title={selectedSession.title} eyebrow="Assistente de IA">
      <div className="status-row"><StatusBadge status={runtimeReady ? "success" : "warning"}>{`● ${runtimeLabel}`}</StatusBadge><StatusBadge>{mode === "read_only" ? "Sessão somente leitura" : "Alterações permitidas"}</StatusBadge></div>
      {mode === "workspace_write" && instruction.trim() && !requiresWorkspaceWrite(instruction) ? <p role="status">Esta tarefa parece analítica. Considere voltar para Somente leitura. O modo não será alterado automaticamente.</p> : null}
      {statusFailed ? <Button onClick={() => { setStatus(null); setStatusFailed(false); setStatusAttempt((value) => value + 1); }}>Verificar novamente</Button> : status === null ? null : !runtimeReady ? <p><Link href="/settings/ai">Configurar assistente de IA</Link></p> : <form className="engineering-form" onSubmit={submit}><fieldset className="mode-selector" disabled={submitting}><legend>Modo de execução</legend><label><input type="radio" name="execution-mode" value="read_only" checked={mode === "read_only"} onChange={() => { setMode("read_only"); setConfirmingWrite(false); setPreparation(null); }} /> Somente leitura</label><label><input type="radio" name="execution-mode" value="workspace_write" checked={mode === "workspace_write"} onChange={() => setMode("workspace_write")} /> Permitir alterações no projeto</label></fieldset><label>Tarefa<textarea placeholder="Descreva o que você quer que o Codex faça neste projeto..." value={instruction} onChange={(event) => setInstruction(event.target.value)} disabled={submitting || preparation !== null} /></label>{error ? <p role="alert" className="engineering-form__error">{error}</p> : null}<Button type="submit" disabled={submitting || preparation !== null}>{submitting ? (mode === "workspace_write" ? "Preparando plano…" : "Executando…") : mode === "workspace_write" ? "Preparar plano" : "Executar com Codex"}</Button></form>}
      {confirmingWrite && preparation ? <section role="alertdialog" aria-labelledby="write-confirmation-title"><h3 id="write-confirmation-title">Revisar e aprovar plano</h3><p>O workspace ainda não foi alterado. Após a aprovação, o plano abaixo poderá criar, modificar ou excluir arquivos.</p><dl className="execution-facts"><div><dt>Execution ID</dt><dd><code>{preparation.execution_id}</code></dd></div><div><dt>Projeto</dt><dd>{projectName}</dd></div><div><dt>Workspace</dt><dd>{workspaceLabel}</dd></div><div><dt>Linguagens</dt><dd>{preparation.analysis.languages.join(", ") || "Não detectadas"}</dd></div><div><dt>Frameworks</dt><dd>{preparation.analysis.frameworks.join(", ") || "Não detectados"}</dd></div></dl><h4>Plano operacional</h4><ol>{preparation.operational_plan.steps.map((step) => <li key={step.step_id}><strong>{step.description}</strong><p>Dependências: {step.dependencies.join(", ") || "nenhuma"}</p><p>Targets: {step.target_hints.join(", ") || "nenhum"}</p><p>Validators: {step.validation_hints.join(", ") || "nenhum"}</p></li>)}</ol><Button onClick={cancelPreparation} disabled={submitting}>Cancelar</Button><Button onClick={run} disabled={submitting}>Aprovar e executar</Button></section> : null}
      {navigationError ? <p role="status">{navigationError}</p> : null}
      {result ? <div className="runtime-result"><p>Modo: {formatExecutionMode(result.execution_mode)}</p><ProjectExecutionEvidence evidence={result} changes={result.changes} output={result.output} /><ContextUsage count={result.context_entry_count} truncated={result.context_truncated} charCount={result.context_char_count} omittedCount={result.context_omitted_execution_count} /><MemoryUsage count={result.memory_entry_count} charCount={result.memory_char_count} truncated={result.memory_truncated} /></div> : null}
      {result ? <ExecutionAIUsage projectId={projectId} executionId={result.execution_id} service={api} /> : null}
    </Card> : null}
    {selectedSession ? <Card title="Memória da sessão" eyebrow="Informações duráveis"><form className="engineering-form" onSubmit={addMemory}><label>Tipo<select value={memoryKind} onChange={(event) => setMemoryKind(event.target.value as SessionMemoryKind)} disabled={addingMemory}><option value="fact">Fato</option><option value="decision">Decisão</option><option value="constraint">Restrição</option><option value="artifact">Artefato</option><option value="goal">Objetivo</option></select></label><label>Memória<input placeholder="Registre uma informação importante desta sessão" value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} disabled={addingMemory} /></label>{memoryError ? <p role="alert">{memoryError}</p> : null}<Button type="submit" disabled={addingMemory}>{addingMemory ? "Adicionando…" : "Adicionar memória"}</Button></form>{memory === null ? <p role="status">Carregando memória...</p> : memory.length === 0 ? <p>Nenhuma memória nesta sessão.</p> : <ul>{memory.map((entry) => <li key={entry.memory_id}><strong>{formatMemoryKind(entry.kind)}</strong> {entry.content}<small>{entry.source_execution_id ? `Execução ${entry.source_execution_id}` : "Manual"}</small></li>)}</ul>}</Card> : null}
    {selectedSession ? <Card title="Histórico" eyebrow="Execuções">{historyRefreshError ? <p role="status">{historyRefreshError}</p> : null}{history === null ? <p role="status">Carregando histórico...</p> : history.length === 0 ? <p>Nenhuma execução ainda.</p> : <ul className="project-runtime-selection-list">{history.map((execution) => <li key={execution.execution_id}><button type="button" onClick={() => { setSelectedExecution(execution); setExecutionLoadError(null); onNavigate?.(selectedSession.session_id, execution.execution_id); }} aria-pressed={visibleSelectedExecution?.execution_id === execution.execution_id}><strong>{formatExecutionStatus(execution.status)}</strong> · {execution.runtime_id} · {formatExecutionMode(execution.execution_mode)}<br />{execution.instruction}<br />{execution.changes.length} arquivos alterados{execution.usage?.input_units != null ? ` · ${execution.usage.input_units} tokens de entrada` : ""}{execution.usage?.output_units != null ? ` · ${execution.usage.output_units} tokens de saída` : ""}</button></li>)}</ul>}</Card> : null}
    {executionLoadError ? <div role="alert" className="dashboard-state dashboard-state--error"><p>{executionLoadError}</p><Button onClick={() => setExecutionAttempt((value) => value + 1)}>Tentar novamente</Button></div> : null}
    {visibleSelectedExecution ? <Card title="Detalhes da execução" eyebrow={formatExecutionStatus(visibleSelectedExecution.status)}><p><strong>Tarefa</strong><br />{visibleSelectedExecution.instruction}</p><ProjectExecutionEvidence evidence={visibleSelectedExecution} changes={visibleSelectedExecution.changes} output={visibleSelectedExecution.output} /><ContextUsage count={visibleSelectedExecution.context_entry_count} truncated={visibleSelectedExecution.context_truncated} charCount={visibleSelectedExecution.context_char_count} omittedCount={visibleSelectedExecution.context_omitted_execution_count} /><MemoryUsage count={visibleSelectedExecution.memory_entry_count} charCount={visibleSelectedExecution.memory_char_count} truncated={visibleSelectedExecution.memory_truncated} /><dl className="execution-facts"><div><dt>Assistente</dt><dd>{visibleSelectedExecution.runtime_id}</dd></div><div><dt>Modelo</dt><dd>{visibleSelectedExecution.model ?? "Desconhecido"}</dd></div><div><dt>Modo</dt><dd>{formatExecutionMode(visibleSelectedExecution.execution_mode)}</dd></div></dl></Card> : null}
    {visibleSelectedExecution ? <ExecutionAIUsage projectId={projectId} executionId={visibleSelectedExecution.execution_id} service={api} /> : null}
  </div>;
}

export function requiresWorkspaceWrite(instruction: string): boolean {
  return /\b(implement(?:ar|e|ation)?|criar?|create|alterar?|modify|corrigir?|fix|remover?|delete|adicionar?|add|instalar?|install)\b/i.test(instruction);
}

function executionErrorMessage(
  error: unknown,
  httpFallback = "O Codex não conseguiu concluir a tarefa. A execução com falha permanece no histórico.",
): string {
  if (error instanceof ApiTimeoutError) {
    return "A execução está demorando mais que o esperado. Ela pode continuar sendo processada no servidor. Consulte o histórico para verificar o resultado.";
  }
  if (error instanceof ApiHttpError) return error.status >= 500 ? uncertainExecutionMessage : httpFallback;
  if (error instanceof ApiResponseError) {
    return "O servidor retornou uma resposta inválida. Consulte o histórico para confirmar o resultado da execução.";
  }
  if (error instanceof ApiNetworkError) {
    return "A comunicação com o servidor foi interrompida. A execução pode continuar sendo processada. Consulte o histórico para verificar o resultado.";
  }
  return httpFallback;
}

const uncertainExecutionMessage = "A comunicação foi interrompida antes de confirmar o resultado. A execução pode ter continuado no servidor. Consulte o histórico.";

function isConfirmedExecutionFailure(error: unknown): boolean {
  return error instanceof ApiHttpError
    ? error.status < 500
    : !(error instanceof ApiNetworkError || error instanceof ApiResponseError);
}

function ExecutionAIUsage({ projectId, executionId, service }: { projectId: string; executionId: string; service: ProjectRuntimeWorkspaceService }) {
  const [usage, setUsage] = useState<AIUsageResponseDto | null>(null);
  useEffect(() => {
    let current = true;
    if (!service.getExecutionUsage) return;
    service.getExecutionUsage(projectId, executionId).then((value) => { if (current) setUsage(value); }, () => { if (current) setUsage(null); });
    return () => { current = false; };
  }, [executionId, projectId, service]);
  if (!usage) return null;
  const summary = usage.aggregate;
  return <section aria-label="Consumo de IA"><h3>Consumo de IA</h3><dl className="execution-facts"><div><dt>Chamadas</dt><dd>{summary.calls}</dd></div><div><dt>Tokens conhecidos</dt><dd>{summary.known_total_tokens}</dd></div><div><dt>Usage desconhecida</dt><dd>{summary.calls_with_unknown_usage}</dd></div></dl></section>;
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
