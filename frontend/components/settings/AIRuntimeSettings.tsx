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
    <PageHeader eyebrow="Settings" title="AI Runtime" description="Connect supported AI runtimes without sharing credentials with the platform." />
    {!status && !failed ? <div role="status" className="executions-skeleton"><span className="sr-only">Checking Codex connection</span></div> : null}
    {failed ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Codex status unavailable</h2><p>Check that the API is running, then try again.</p><Button onClick={retry}>Check again</Button></div> : null}
    {status ? <Card eyebrow="AI Runtime" title="Codex">
      <dl className="runtime-status">
        <div><dt>Installation</dt><dd>{status.installed ? <StatusBadge status="success">Installed</StatusBadge> : <StatusBadge status="danger">Not installed</StatusBadge>}</dd></div>
        <div><dt>Version</dt><dd>{status.version ?? "Unavailable"}</dd></div>
        <div><dt>Authentication</dt><dd>{status.authenticated ? <StatusBadge status="success">Connected</StatusBadge> : <StatusBadge status="warning">Not connected</StatusBadge>}</dd></div>
        <div><dt>Status</dt><dd>{status.ready ? <StatusBadge status="success">Ready</StatusBadge> : <StatusBadge status="warning">Unavailable</StatusBadge>}</dd></div>
      </dl>
      {!status.installed ? <div className="runtime-guidance"><p>Codex is required to use this runtime.</p><a href="https://developers.openai.com/codex/cli/" target="_blank" rel="noreferrer">Installation instructions</a></div> : null}
      {status.state === "not_authenticated" ? <div className="runtime-guidance"><p>Connect your Codex account with the official client:</p><code>{status.authentication_command ?? "codex login"}</code><p>ASEP never receives your password or tokens.</p></div> : null}
      <Button variant="secondary" onClick={retry}>Check again</Button>
    </Card> : null}
  </div>;
}
