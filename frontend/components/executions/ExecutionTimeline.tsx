import type { TimelineEventDto } from "../../lib/api/dtos";
import { formatTimestamp } from "./formatters";

function metadataSummary(metadata: TimelineEventDto["metadata"]): string | null {
  const keys = Object.keys(metadata).sort();
  return keys.length ? keys.map((key) => `${key}: ${JSON.stringify(metadata[key])}`).join(" · ") : null;
}

export function ExecutionTimeline({ events }: { events: readonly TimelineEventDto[] }) {
  if (!events.length) return <p className="execution-muted">No timeline events recorded.</p>;
  return <ol className="execution-timeline" aria-label="Execution timeline">{events.map((event) => {
    const metadata = metadataSummary(event.metadata);
    return <li key={event.id}><div className="execution-timeline__marker" aria-hidden="true" /><div>
      <div className="execution-timeline__heading"><strong>{event.type}</strong><time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time></div>
      {event.stage_id ? <p>Stage: {event.stage_id}</p> : null}{event.message ? <p>{event.message}</p> : null}
      {metadata ? <p className="execution-timeline__metadata">{metadata}</p> : null}
    </div></li>;
  })}</ol>;
}
