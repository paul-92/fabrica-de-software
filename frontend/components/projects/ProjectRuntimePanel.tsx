"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto, ProjectExecutionDto, ProjectSessionDto } from "../../lib/api/dtos";
import { createProjectRuntimeWorkspaceService, type ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";

type Props = { projectId: string; projectName: string; workspacePath: string; service?: ProjectRuntimeWorkspaceService };

export function ProjectRuntimePanel({ projectId, projectName, workspacePath, service }: Props) {
  const api = useMemo(() => service ?? createProjectRuntimeWorkspaceService(), [service]);
  const [status, setStatus] = useState<AIRuntimeStatusDto | null>(null);
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

  useEffect(() => {
    let active = true;
    api.status().then((value) => { if (active) setStatus(value); }, () => { if (active) setStatus(null); });
    api.listSessions(projectId).then((items) => { if (active) { setSessions(items); setSessionsLoadError(false); setHistory(null); setSelectedExecution(null); setResult(null); setSelectedSession(items[0] ?? null); } }, () => { if (active) { setSessions([]); setSessionsLoadError(true); } });
    return () => { active = false; };
  }, [api, projectId, sessionsAttempt]);

  useEffect(() => {
    if (!selectedSession) return;
    let active = true;
    api.listExecutions(projectId, selectedSession.session_id).then((items) => { if (active) setHistory(items); }, () => { if (active) setHistory([]); });
    return () => { active = false; };
  }, [api, projectId, selectedSession]);

  async function createSession(event: FormEvent) {
    event.preventDefault(); if (creatingSession) return;
    if (!sessionTitle.trim()) { setSessionError("Session title is required."); return; }
    setCreatingSession(true); setSessionError(null);
    try {
      const created = await api.createSession(projectId, sessionTitle.trim());
      setSessions((items) => [created, ...(items ?? [])]);
      setHistory(null); setSelectedExecution(null); setResult(null); setSelectedSession(created); setSessionTitle("");
    } catch { setSessionError("Session could not be created. Try again."); }
    finally { setCreatingSession(false); }
  }

  async function run() {
    if (submitting || !selectedSession) return;
    setSubmitting(true); setError(null); setResult(null); setConfirmingWrite(false);
    try {
      const completed = await api.execute(projectId, selectedSession.session_id, instruction.trim(), mode);
      setResult(completed);
      setHistory(await api.listExecutions(projectId, selectedSession.session_id));
    } catch {
      setError("Codex could not complete the request. The failed execution remains in history.");
      setHistory(await api.listExecutions(projectId, selectedSession.session_id).catch(() => []));
    } finally { setSubmitting(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); if (submitting) return;
    if (!instruction.trim()) { setError("Instruction is required."); return; }
    if (mode === "workspace_write") { setConfirmingWrite(true); return; }
    await run();
  }

  return <div className="page-stack">
    <Card title="Sessions" eyebrow="Project work"><form className="engineering-form" onSubmit={createSession}><label>Session title<input value={sessionTitle} onChange={(event) => setSessionTitle(event.target.value)} disabled={creatingSession} /></label>{sessionError ? <p role="alert" className="engineering-form__error">{sessionError}</p> : null}<Button type="submit" disabled={creatingSession}>{creatingSession ? "Creating…" : "New session"}</Button></form>{sessions === null ? <p role="status">Loading sessions</p> : sessionsLoadError ? <div role="alert"><p>Sessions could not be loaded.</p><Button onClick={() => { setSessions(null); setSessionsAttempt((value) => value + 1); }}>Retry sessions</Button></div> : sessions.length === 0 ? <p>No sessions yet.</p> : <ul>{sessions.map((session) => <li key={session.session_id}><button type="button" onClick={() => { setHistory(null); setSelectedExecution(null); setResult(null); setError(null); setConfirmingWrite(false); setSelectedSession(session); }} aria-pressed={selectedSession?.session_id === session.session_id}>{session.title}</button></li>)}</ul>}</Card>
    {selectedSession ? <Card title={selectedSession.title} eyebrow="AI Runtime">
      <div className="status-row"><StatusBadge status={status?.ready ? "success" : "warning"}>{status?.ready ? "Ready" : "Not connected"}</StatusBadge><StatusBadge>{mode === "read_only" ? "Read-only session" : "Workspace write"}</StatusBadge></div>
      {!status?.ready ? <p><Link href="/settings/ai">Configure AI Runtime</Link></p> : <form className="engineering-form" onSubmit={submit}><fieldset disabled={submitting}><legend>Execution mode</legend><label><input type="radio" name="execution-mode" value="read_only" checked={mode === "read_only"} onChange={() => { setMode("read_only"); setConfirmingWrite(false); }} /> Read only</label><label><input type="radio" name="execution-mode" value="workspace_write" checked={mode === "workspace_write"} onChange={() => setMode("workspace_write")} /> Allow workspace changes</label></fieldset><label>Task<textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} disabled={submitting} /></label>{error ? <p role="alert" className="engineering-form__error">{error}</p> : null}<Button type="submit" disabled={submitting}>{submitting ? "Running — workspace may be changing…" : "Run with Codex"}</Button></form>}
      {confirmingWrite ? <section role="alertdialog" aria-labelledby="write-confirmation-title"><h3 id="write-confirmation-title">Confirm workspace write</h3><p>Codex may create, modify, or delete files inside this registered workspace. Changes are not rolled back automatically.</p><dl><div><dt>Project</dt><dd>{projectName}</dd></div><div><dt>Workspace</dt><dd>{workspacePath}</dd></div><div><dt>Mode</dt><dd>workspace_write</dd></div></dl><Button onClick={() => setConfirmingWrite(false)} disabled={submitting}>Cancel</Button><Button onClick={run} disabled={submitting}>Confirm and run</Button></section> : null}
      {result ? <div className="runtime-result"><h3>Codex result</h3><pre>{result.output}</pre><p>Execution mode: {result.execution_mode}</p><ContextUsage count={result.context_entry_count} truncated={result.context_truncated} /><h4>Workspace changes</h4>{result.changes.length === 0 ? <p>No workspace changes detected.</p> : <ChangeList changes={result.changes} />}</div> : null}
    </Card> : null}
    {selectedSession ? <Card title="History" eyebrow="Executions">{history === null ? <p role="status">Loading execution history</p> : history.length === 0 ? <p>No executions yet.</p> : <ul>{history.map((execution) => <li key={execution.execution_id}><button type="button" onClick={() => setSelectedExecution(execution)}><strong>{execution.status}</strong> · {execution.runtime_id} · {execution.execution_mode}<br />{execution.instruction}<br />{execution.changes.length} files changed{execution.usage?.input_units != null ? ` · ${execution.usage.input_units} input tokens` : ""}{execution.usage?.output_units != null ? ` · ${execution.usage.output_units} output tokens` : ""}</button></li>)}</ul>}</Card> : null}
    {selectedExecution ? <Card title="Execution details" eyebrow={selectedExecution.status}><p><strong>Instruction</strong><br />{selectedExecution.instruction}</p><p><strong>Result</strong><br />{selectedExecution.output ?? "No result output."}</p><ContextUsage count={selectedExecution.context_entry_count} truncated={selectedExecution.context_truncated} /><dl className="execution-facts"><div><dt>Runtime</dt><dd>{selectedExecution.runtime_id}</dd></div><div><dt>Model</dt><dd>{selectedExecution.model ?? "Unknown"}</dd></div><div><dt>Mode</dt><dd>{selectedExecution.execution_mode}</dd></div><div><dt>Status</dt><dd>{selectedExecution.status}</dd></div>{selectedExecution.error_code ? <div><dt>Error</dt><dd>{selectedExecution.error_code}</dd></div> : null}</dl><h4>Workspace changes</h4>{selectedExecution.changes.length ? <ChangeList changes={selectedExecution.changes} /> : <p>No workspace changes detected.</p>}</Card> : null}
  </div>;
}

function ContextUsage({ count, truncated }: { count: number; truncated: boolean }) {
  if (count === 0) return null;
  return <p>Using context from {count} previous {count === 1 ? "execution" : "executions"}.{truncated ? " Context limited to recent history." : ""}</p>;
}

function ChangeList({ changes }: { changes: ProjectAIRuntimeExecutionDto["changes"] }) {
  return <ul>{changes.map((change) => <li key={`${change.change_type}:${change.path}`}><strong>{change.change_type}</strong> {change.path}</li>)}</ul>;
}
