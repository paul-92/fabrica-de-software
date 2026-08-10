import type { RunDto, TimelineEventDto } from "../../lib/api/dtos";
import { Button } from "../Button";
import { Card } from "../Card";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { formatDuration, formatTimestamp } from "./formatters";

export function ExecutionDetails({ run, timeline, timelineLoading, timelineError, retryTimeline }: {
  run: RunDto; timeline: readonly TimelineEventDto[] | null; timelineLoading: boolean; timelineError: boolean; retryTimeline(): void;
}) {
  return <Card title={run.id} eyebrow="Detalhes da execução" action={<ExecutionStatusBadge status={run.status} />}>
    <dl className="execution-facts">
      <div><dt>Projeto</dt><dd>{run.project_id ?? "—"}</dd></div><div><dt>Fluxo</dt><dd>{run.workflow_id ?? "—"}</dd></div>
      <div><dt>Etapa</dt><dd>{run.stage_id ?? "—"}</dd></div><div><dt>Provedor</dt><dd>{run.provider_name ?? "—"}</dd></div>
      <div><dt>Início</dt><dd>{formatTimestamp(run.started_at)}</dd></div><div><dt>Término</dt><dd>{formatTimestamp(run.finished_at)}</dd></div>
      <div><dt>Duração</dt><dd>{formatDuration(run.started_at, run.finished_at)}</dd></div>
    </dl>
    {run.summary ? <p>{run.summary}</p> : null}
    {run.error ? <div className="execution-inline-error" role="alert"><strong>{run.error.type}</strong><p>{run.error.message}</p></div> : null}
    <section className="execution-timeline-section" aria-labelledby="timeline-title"><h3 id="timeline-title">Linha do tempo</h3>
      {timelineLoading ? <p role="status">Carregando linha do tempo</p> : null}
      {timelineError ? <div className="execution-inline-error" role="alert"><p>Não foi possível carregar a linha do tempo.</p><Button onClick={retryTimeline}>Tentar novamente</Button></div> : null}
      {!timelineLoading && !timelineError && timeline ? <ExecutionTimeline events={timeline} /> : null}
    </section>
  </Card>;
}
