"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { AIRuntimeStatusDto, ProjectAIRuntimeExecutionDto } from "../../lib/api/dtos";
import { createProjectRuntimeWorkspaceService, type ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";

export function ProjectRuntimePanel({ projectId, service }: { projectId: string; service?: ProjectRuntimeWorkspaceService }) {
  const api = useMemo(() => service ?? createProjectRuntimeWorkspaceService(), [service]);
  const [status, setStatus] = useState<AIRuntimeStatusDto | null>(null);
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectAIRuntimeExecutionDto | null>(null);

  useEffect(() => { let active = true; api.status().then((value) => { if (active) setStatus(value); }, () => { if (active) setStatus(null); }); return () => { active = false; }; }, [api]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    if (!instruction.trim()) { setError("Instruction is required."); return; }
    setSubmitting(true); setError(null); setResult(null);
    try { setResult(await api.execute(projectId, instruction.trim())); }
    catch { setError("Codex could not complete the request. Try again."); }
    finally { setSubmitting(false); }
  }
  return <Card title="Codex" eyebrow="AI Runtime">
    <div className="status-row"><StatusBadge status={status?.ready ? "success" : "warning"}>{status?.ready ? "Ready" : "Not connected"}</StatusBadge><StatusBadge>Read-only session</StatusBadge></div>
    {!status?.ready ? <p><Link href="/settings/ai">Configure AI Runtime</Link></p> : <form className="engineering-form" onSubmit={submit}>
      <label>Task<textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} disabled={submitting} /></label>
      {error ? <p role="alert" className="engineering-form__error">{error}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? "Running…" : "Run with Codex"}</Button>
    </form>}
    {result ? <div className="runtime-result"><h3>Codex result</h3><pre>{result.output}</pre><dl className="execution-facts"><div><dt>Runtime</dt><dd>{result.runtime_id}</dd></div><div><dt>Model</dt><dd>{result.model_id}</dd></div>{result.usage?.input_units != null ? <div><dt>Input tokens</dt><dd>{result.usage.input_units}</dd></div> : null}{result.usage?.output_units != null ? <div><dt>Output tokens</dt><dd>{result.usage.output_units}</dd></div> : null}{result.usage?.total_units != null ? <div><dt>Total tokens</dt><dd>{result.usage.total_units}</dd></div> : null}</dl></div> : null}
  </Card>;
}
