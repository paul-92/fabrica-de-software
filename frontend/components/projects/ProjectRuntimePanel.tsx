"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { AIRuntimeExecutionMode, AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto } from "../../lib/api/dtos";
import { createProjectRuntimeWorkspaceService, type ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";

type Props = {
  projectId: string;
  projectName: string;
  workspacePath: string;
  service?: ProjectRuntimeWorkspaceService;
};

export function ProjectRuntimePanel({ projectId, projectName, workspacePath, service }: Props) {
  const api = useMemo(() => service ?? createProjectRuntimeWorkspaceService(), [service]);
  const [status, setStatus] = useState<AIRuntimeStatusDto | null>(null);
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState<AIRuntimeExecutionMode>("read_only");
  const [confirmingWrite, setConfirmingWrite] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectAIRuntimeExecutionDto | null>(null);

  useEffect(() => {
    let active = true;
    api.status().then((value) => { if (active) setStatus(value); }, () => { if (active) setStatus(null); });
    return () => { active = false; };
  }, [api]);

  async function run() {
    if (submitting) return;
    setSubmitting(true); setError(null); setResult(null); setConfirmingWrite(false);
    try { setResult(await api.execute(projectId, instruction.trim(), mode)); }
    catch { setError("Codex could not complete the request. Try again."); }
    finally { setSubmitting(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    if (!instruction.trim()) { setError("Instruction is required."); return; }
    if (mode === "workspace_write") { setConfirmingWrite(true); return; }
    await run();
  }

  return <Card title="Codex" eyebrow="AI Runtime">
    <div className="status-row"><StatusBadge status={status?.ready ? "success" : "warning"}>{status?.ready ? "Ready" : "Not connected"}</StatusBadge><StatusBadge>{mode === "read_only" ? "Read-only session" : "Workspace write"}</StatusBadge></div>
    {!status?.ready ? <p><Link href="/settings/ai">Configure AI Runtime</Link></p> : <form className="engineering-form" onSubmit={submit}>
      <fieldset disabled={submitting}><legend>Execution mode</legend><label><input type="radio" name="execution-mode" value="read_only" checked={mode === "read_only"} onChange={() => { setMode("read_only"); setConfirmingWrite(false); }} /> Read only</label><label><input type="radio" name="execution-mode" value="workspace_write" checked={mode === "workspace_write"} onChange={() => setMode("workspace_write")} /> Allow workspace changes</label></fieldset>
      <label>Task<textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} disabled={submitting} /></label>
      {error ? <p role="alert" className="engineering-form__error">{error}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? "Running…" : "Run with Codex"}</Button>
    </form>}
    {confirmingWrite ? <section role="alertdialog" aria-labelledby="write-confirmation-title"><h3 id="write-confirmation-title">Confirm workspace write</h3><p>Codex may create, modify, or delete files inside this registered workspace. Changes are not rolled back automatically.</p><dl><div><dt>Project</dt><dd>{projectName}</dd></div><div><dt>Workspace</dt><dd>{workspacePath}</dd></div><div><dt>Mode</dt><dd>workspace_write</dd></div></dl><Button onClick={() => setConfirmingWrite(false)} disabled={submitting}>Cancel</Button><Button onClick={run} disabled={submitting}>Confirm and run</Button></section> : null}
    {result ? <div className="runtime-result"><h3>Codex result</h3><pre>{result.output}</pre><dl className="execution-facts"><div><dt>Runtime</dt><dd>{result.runtime_id}</dd></div><div><dt>Model</dt><dd>{result.model_id}</dd></div><div><dt>Execution mode</dt><dd>{result.execution_mode}</dd></div>{result.usage?.input_units != null ? <div><dt>Input tokens</dt><dd>{result.usage.input_units}</dd></div> : null}{result.usage?.output_units != null ? <div><dt>Output tokens</dt><dd>{result.usage.output_units}</dd></div> : null}{result.usage?.total_units != null ? <div><dt>Total tokens</dt><dd>{result.usage.total_units}</dd></div> : null}</dl><h4>Workspace changes</h4>{result.changes.length === 0 ? <p>No workspace changes detected.</p> : <ul>{result.changes.map((change) => <li key={`${change.change_type}:${change.path}`}><strong>{change.change_type}</strong> {change.path}</li>)}</ul>}</div> : null}
  </Card>;
}
