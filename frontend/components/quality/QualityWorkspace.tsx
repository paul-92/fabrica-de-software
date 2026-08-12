"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import type {
  ProviderMetricDto,
  SequentialQualityGateDecision,
  SequentialQualityGateDto,
  StatusMetricDto,
} from "../../lib/api/dtos";
import { ApiHttpError } from "../../lib/api/errors";
import { formatExecutionStatus } from "../../lib/presentation";
import {
  createQualityLoader,
  type QualityData,
  type QualityLoader,
} from "../../lib/services/quality";
import {
  createSequentialQualityLoader,
  type SequentialQualityLoader,
} from "../../lib/services/sequentialQuality";
import { Button } from "../Button";
import { Card } from "../Card";
import { DashboardMetrics } from "../dashboard/DashboardMetrics";
import { MetricCard } from "../dashboard/MetricCard";
import { RecentRuns } from "../dashboard/RecentRuns";
import { PageHeader } from "../layout/PageHeader";
import { StatusBadge } from "../StatusBadge";

type QualityState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: QualityData };

export function QualityWorkspace({
  loader,
  sequentialLoader,
}: {
  loader?: QualityLoader;
  sequentialLoader?: SequentialQualityLoader;
}) {
  const effectiveLoader = useMemo(() => loader ?? createQualityLoader(), [loader]);
  const effectiveSequentialLoader = useMemo(
    () => sequentialLoader ?? createSequentialQualityLoader(),
    [sequentialLoader],
  );
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<QualityState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    effectiveLoader.load().then(
      (data) => { if (current) setState({ status: "ready", data }); },
      () => { if (current) setState({ status: "error" }); },
    );
    return () => { current = false; };
  }, [effectiveLoader, attempt]);

  function retry() {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Garantia" title="Qualidade" description="Acompanhe resultados operacionais, tendências de execução e evidências públicas da plataforma." />
    {state.status === "loading" ? <div className="executions-skeleton" role="status"><span className="sr-only">Carregando indicadores de qualidade</span></div> : null}
    {state.status === "error" ? <div className="dashboard-state dashboard-state--error" role="alert"><h2>Qualidade indisponível</h2><p>Não foi possível carregar os indicadores de qualidade.</p><Button onClick={retry}>Tentar novamente</Button></div> : null}
    {state.status === "ready" ? <QualityContent data={state.data} /> : null}
    <SequentialQualityExplorer loader={effectiveSequentialLoader} />
  </div>;
}

type SequentialState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; items: readonly SequentialQualityGateDto[] }
  | { status: "error"; kind: "not-found" | "operational" };

function SequentialQualityExplorer({ loader }: { loader: SequentialQualityLoader }) {
  const [projectId, setProjectId] = useState("");
  const [executionId, setExecutionId] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [state, setState] = useState<SequentialState>({ status: "idle" });
  const [lastQuery, setLastQuery] = useState<Readonly<{
    projectId: string;
    executionId: string;
  }> | null>(null);

  async function query(project: string, execution: string) {
    setState({ status: "loading" });
    try {
      const items = await loader.load(project, execution);
      setState({ status: "ready", items });
    } catch (error) {
      setState({
        status: "error",
        kind: error instanceof ApiHttpError && error.status === 404
          ? "not-found"
          : "operational",
      });
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const project = projectId.trim();
    const execution = executionId.trim();
    if (!project || !execution) {
      setValidationError("Informe o projeto sequencial e a execução.");
      return;
    }
    setValidationError(null);
    const submitted = { projectId: project, executionId: execution };
    setLastQuery(submitted);
    void query(submitted.projectId, submitted.executionId);
  }

  return <Card title="Quality Gates sequenciais" eyebrow="Consulta detalhada">
    <p className="sequential-quality__description">Consulte resultados pelo identificador declarativo do projeto sequencial e pelo identificador da execução.</p>
    <form className="sequential-quality__form" onSubmit={submit}>
      <label htmlFor="sequential-project-id">Projeto sequencial</label>
      <input id="sequential-project-id" value={projectId} onChange={(event) => setProjectId(event.target.value)} disabled={state.status === "loading"} autoComplete="off" />
      <label htmlFor="sequential-execution-id">Execução sequencial</label>
      <input id="sequential-execution-id" value={executionId} onChange={(event) => setExecutionId(event.target.value)} disabled={state.status === "loading"} autoComplete="off" />
      {validationError ? <p className="sequential-quality__message" role="alert">{validationError}</p> : null}
      <Button type="submit" disabled={state.status === "loading"}>{state.status === "loading" ? "Consultando…" : "Consultar Quality Gates"}</Button>
    </form>
    {state.status === "idle" ? <p className="sequential-quality__idle">Informe os identificadores para iniciar a consulta.</p> : null}
    {state.status === "loading" ? <p className="sequential-quality__message" role="status">Carregando Quality Gates sequenciais…</p> : null}
    {state.status === "error" ? <div className="sequential-quality__message" role="alert"><p>{state.kind === "not-found" ? "Não foi possível localizar os resultados desta execução sequencial." : "Não foi possível consultar os Quality Gates no momento."}</p>{lastQuery ? <Button type="button" variant="secondary" onClick={() => void query(lastQuery.projectId, lastQuery.executionId)}>Tentar novamente</Button> : null}</div> : null}
    {state.status === "ready" && state.items.length === 0 ? <p className="sequential-quality__message" role="status">Nenhum Quality Gate registrado para esta execução.</p> : null}
    {state.status === "ready" && state.items.length > 0 ? <QualityGateResults items={state.items} /> : null}
  </Card>;
}

function QualityGateResults({ items }: { items: readonly SequentialQualityGateDto[] }) {
  return <div className="sequential-quality__results">{items.map((item) => <article className="sequential-quality__gate" key={`${item.stage_id}:${item.gate_id}`}>
    <header><div><p className="eyebrow">{item.stage_id}</p><h3>{item.gate_id}</h3></div><StatusBadge status={decisionStatus(item.decision)}>{decisionLabel(item.decision)}</StatusBadge></header>
    <dl><div><dt>Execução</dt><dd>{item.execution_id}</dd></div><div><dt>Avaliado em</dt><dd><time dateTime={item.evaluated_at}>{formatQualityDate(item.evaluated_at)}</time></dd></div></dl>
    <div className="sequential-quality__criteria"><Criteria title="Critérios atendidos" items={item.satisfied_criteria} empty="Nenhum critério atendido registrado." /><Criteria title="Critérios não atendidos" items={item.unsatisfied_criteria} empty="Nenhum critério não atendido registrado." /></div>
  </article>)}</div>;
}

function Criteria({ title, items, empty }: { title: string; items: readonly string[]; empty: string }) {
  return <section><h4>{title}</h4>{items.length === 0 ? <p>{empty}</p> : <ul>{items.map((criterion, index) => <li key={`${index}:${criterion}`}>{criterion}</li>)}</ul>}</section>;
}

function decisionLabel(decision: SequentialQualityGateDecision): string {
  if (decision === "APPROVED") return "Aprovado";
  if (decision === "APPROVED_WITH_PENDING") return "Aprovado com pendências";
  return "Bloqueado";
}

function decisionStatus(decision: SequentialQualityGateDecision): "success" | "warning" | "danger" {
  if (decision === "APPROVED") return "success";
  if (decision === "APPROVED_WITH_PENDING") return "warning";
  return "danger";
}

function formatQualityDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data indisponível";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function QualityContent({ data }: { data: QualityData }) {
  const hasData = data.summary.total_runs > 0 || data.statuses.length > 0 || data.providers.length > 0 || data.recentRuns.length > 0;
  if (!hasData) return <div className="dashboard-state"><h2>Nenhum dado de qualidade ainda</h2><p>Os indicadores aparecerão quando a plataforma registrar execuções.</p></div>;
  return <>
    <DashboardMetrics metrics={data.summary} />
    <section className="quality-rates" aria-label="Taxas de qualidade">
      <MetricCard label="Taxa de sucesso" value={formatRate(data.summary.success_rate)} detail={`${data.summary.eligible_runs} execuções elegíveis`} />
      <MetricCard label="Taxa de falha" value={formatRate(data.summary.failure_rate)} detail={`${data.summary.eligible_runs} execuções elegíveis`} />
    </section>
    <div className="quality-distributions">
      <StatusDistribution items={data.statuses} />
      <ProviderDistribution items={data.providers} />
    </div>
    {data.recentRuns.length > 0 ? <RecentRuns runs={data.recentRuns} /> : <Card title="Evidências recentes" eyebrow="Execuções"><p>Nenhuma evidência recente disponível.</p></Card>}
  </>;
}

function StatusDistribution({ items }: { items: readonly StatusMetricDto[] }) {
  return <Card title="Distribuição por status" eyebrow="Execuções">
    {items.length === 0 ? <p>Nenhum status disponível.</p> : <dl className="quality-list">{items.map((item) => <div key={item.status}><dt>{formatExecutionStatus(item.status)}</dt><dd>{item.count}</dd></div>)}</dl>}
  </Card>;
}

function ProviderDistribution({ items }: { items: readonly ProviderMetricDto[] }) {
  return <Card title="Distribuição por provedor" eyebrow="Execuções">
    {items.length === 0 ? <p>Nenhum provedor disponível.</p> : <div className="runs-table-wrap"><table className="runs-table quality-provider-table"><thead><tr><th scope="col">Provedor</th><th scope="col">Total</th><th scope="col">Sucesso</th><th scope="col">Falha</th></tr></thead><tbody>{items.map((item) => <tr key={item.provider_name ?? "unknown"}><td>{item.provider_name ?? "Sem provedor"}</td><td>{item.total_runs}</td><td>{formatRate(item.success_rate)}</td><td>{formatRate(item.failure_rate)}</td></tr>)}</tbody></table></div>}
  </Card>;
}

function formatRate(value: number): string {
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}
