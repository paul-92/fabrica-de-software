"use client";

import { useEffect, useMemo, useState } from "react";
import type { RunDto, TimelineEventDto } from "../../lib/api/dtos";
import { createExecutionsLoader, type ExecutionsLoader } from "../../lib/services/executions";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";
import { ExecutionDetails } from "./ExecutionDetails";
import { ExecutionsTable } from "./ExecutionsTable";

type ListState = { status: "loading" } | { status: "error" } | { status: "ready"; runs: readonly RunDto[] };

export function ExecutionsWorkspace({ loader }: { loader?: ExecutionsLoader }) {
  const effectiveLoader = useMemo(() => loader ?? createExecutionsLoader(), [loader]);
  const [listAttempt, setListAttempt] = useState(0);
  const [listState, setListState] = useState<ListState>({ status: "loading" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [details, setDetails] = useState<RunDto | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const [timeline, setTimeline] = useState<readonly TimelineEventDto[] | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState(false);
  const [timelineAttempt, setTimelineAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    effectiveLoader.list().then(
      (runs) => current && setListState({ status: "ready", runs }),
      () => current && setListState({ status: "error" }),
    );
    return () => { current = false; };
  }, [effectiveLoader, listAttempt]);

  useEffect(() => {
    if (selectedId === null) return;
    let current = true;
    effectiveLoader.get(selectedId).then(
      (run) => { if (current) { setDetails(run); setDetailLoading(false); } },
      () => { if (current) { setDetailError(true); setDetailLoading(false); } },
    );
    return () => { current = false; };
  }, [effectiveLoader, selectedId]);

  useEffect(() => {
    if (selectedId === null) return;
    let current = true;
    effectiveLoader.timeline(selectedId).then(
      (events) => { if (current) { setTimeline(events); setTimelineLoading(false); } },
      () => { if (current) { setTimelineError(true); setTimelineLoading(false); } },
    );
    return () => { current = false; };
  }, [effectiveLoader, selectedId, timelineAttempt]);

  function retryList() { setListState({ status: "loading" }); setListAttempt((value) => value + 1); }
  function selectExecution(runId: string) {
    setSelectedId(runId);
    setDetails(null); setDetailError(false); setDetailLoading(true);
    setTimeline(null); setTimelineError(false); setTimelineLoading(true);
  }
  function retryTimeline() {
    setTimeline(null); setTimelineError(false); setTimelineLoading(true);
    setTimelineAttempt((value) => value + 1);
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Operações" title="Execuções" description="Consulte status, evidências e eventos em ordem cronológica." />
    {listState.status === "loading" ? <div className="executions-skeleton" role="status"><span className="sr-only">Carregando execuções</span></div> : null}
    {listState.status === "error" ? <div className="dashboard-state dashboard-state--error" role="alert"><h2>Execuções indisponíveis</h2><p>Não foi possível carregar a lista de execuções.</p><Button onClick={retryList}>Tentar novamente</Button></div> : null}
    {listState.status === "ready" && listState.runs.length === 0 ? <div className="dashboard-state"><h2>Nenhuma execução ainda</h2><p>As execuções aparecerão aqui quando estiverem disponíveis.</p></div> : null}
    {listState.status === "ready" && listState.runs.length > 0 ? <>
      <Card title="Histórico de execuções" eyebrow="Execuções"><ExecutionsTable runs={listState.runs} selectedId={selectedId} onSelect={selectExecution} /></Card>
      {selectedId === null ? <div className="dashboard-state"><h2>Selecione uma execução</h2><p>Abra uma execução para consultar seus detalhes e sua linha do tempo.</p></div> : null}
      {detailLoading ? <div className="execution-detail-skeleton" role="status">Carregando detalhes da execução</div> : null}
      {detailError ? <div className="dashboard-state dashboard-state--error" role="alert"><h2>Detalhes indisponíveis</h2><p>Não foi possível carregar a execução selecionada.</p></div> : null}
      {details ? <ExecutionDetails run={details} timeline={timeline} timelineLoading={timelineLoading} timelineError={timelineError} retryTimeline={retryTimeline} /> : null}
    </> : null}
  </div>;
}
