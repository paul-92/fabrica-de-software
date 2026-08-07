import type { RunDto, TimelineEventDto } from "../../lib/api/dtos";
import { Button } from "../Button";
import { Card } from "../Card";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { formatDuration, formatTimestamp } from "./formatters";

export function ExecutionDetails({ run, timeline, timelineLoading, timelineError, retryTimeline }: {
  run: RunDto; timeline: readonly TimelineEventDto[] | null; timelineLoading: boolean; timelineError: boolean; retryTimeline(): void;
}) {
  return <Card title={run.id} eyebrow="Execution details" action={<ExecutionStatusBadge status={run.status} />}>
    <dl className="execution-facts">
      <div><dt>Project</dt><dd>{run.project_id ?? "—"}</dd></div><div><dt>Workflow</dt><dd>{run.workflow_id ?? "—"}</dd></div>
      <div><dt>Stage</dt><dd>{run.stage_id ?? "—"}</dd></div><div><dt>Provider</dt><dd>{run.provider_name ?? "—"}</dd></div>
      <div><dt>Started</dt><dd>{formatTimestamp(run.started_at)}</dd></div><div><dt>Finished</dt><dd>{formatTimestamp(run.finished_at)}</dd></div>
      <div><dt>Duration</dt><dd>{formatDuration(run.started_at, run.finished_at)}</dd></div>
    </dl>
    {run.summary ? <p>{run.summary}</p> : null}
    {run.error ? <div className="execution-inline-error" role="alert"><strong>{run.error.type}</strong><p>{run.error.message}</p></div> : null}
    <section className="execution-timeline-section" aria-labelledby="timeline-title"><h3 id="timeline-title">Timeline</h3>
      {timelineLoading ? <p role="status">Loading timeline</p> : null}
      {timelineError ? <div className="execution-inline-error" role="alert"><p>Timeline could not be loaded.</p><Button onClick={retryTimeline}>Try timeline again</Button></div> : null}
      {!timelineLoading && !timelineError && timeline ? <ExecutionTimeline events={timeline} /> : null}
    </section>
  </Card>;
}
