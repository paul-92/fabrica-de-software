import type { RunDto } from "../../lib/api/dtos";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { formatDuration, formatTimestamp } from "./formatters";

export function ExecutionsTable({ runs, selectedId, onSelect }: {
  runs: readonly RunDto[];
  selectedId: string | null;
  onSelect(runId: string): void;
}) {
  return <div className="runs-table-wrap"><table className="runs-table executions-table">
    <thead><tr><th scope="col">Execution</th><th scope="col">Status</th><th scope="col">Project</th><th scope="col">Started</th><th scope="col">Finished</th><th scope="col">Duration</th><th scope="col">Provider</th><th scope="col">Result</th></tr></thead>
    <tbody>{runs.map((run) => <tr key={run.id} aria-current={selectedId === run.id ? "true" : undefined}>
      <td className="runs-table__id"><button className="execution-select" type="button" onClick={() => onSelect(run.id)} aria-label={`Open execution ${run.id}`}>{run.id}</button></td>
      <td><ExecutionStatusBadge status={run.status} /></td><td>{run.project_id ?? "—"}</td>
      <td>{formatTimestamp(run.started_at)}</td><td>{formatTimestamp(run.finished_at)}</td><td>{formatDuration(run.started_at, run.finished_at)}</td>
      <td>{run.provider_name ?? "—"}</td><td className="runs-table__result">{run.error?.message ?? run.summary ?? "—"}</td>
    </tr>)}</tbody>
  </table></div>;
}
