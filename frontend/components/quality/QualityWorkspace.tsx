"use client";

import { useEffect, useMemo, useState } from "react";
import type { ProviderMetricDto, StatusMetricDto } from "../../lib/api/dtos";
import { formatExecutionStatus } from "../../lib/presentation";
import { createQualityLoader, type QualityData, type QualityLoader } from "../../lib/services/quality";
import { Button } from "../Button";
import { Card } from "../Card";
import { DashboardMetrics } from "../dashboard/DashboardMetrics";
import { MetricCard } from "../dashboard/MetricCard";
import { RecentRuns } from "../dashboard/RecentRuns";
import { PageHeader } from "../layout/PageHeader";

type QualityState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: QualityData };

export function QualityWorkspace({ loader }: { loader?: QualityLoader }) {
  const effectiveLoader = useMemo(() => loader ?? createQualityLoader(), [loader]);
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
  </div>;
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
