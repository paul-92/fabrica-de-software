import type { RunDto } from "../../lib/api/dtos";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { formatDuration, formatTimestamp } from "./formatters";

export function ExecutionsTable({ runs, selectedId, onSelect }: {
  runs: readonly RunDto[];
  selectedId: string | null;
  onSelect(runId: string): void;
}) {
  return <div className="runs-table-wrap"><table className="runs-table executions-table">
    <thead><tr><th scope="col">Execução</th><th scope="col">Status</th><th scope="col">Projeto</th><th scope="col">Início</th><th scope="col">Término</th><th scope="col">Duração</th><th scope="col">Provedor</th><th scope="col">Resultado</th></tr></thead>
    <tbody>{runs.map((run) => <tr key={run.id} aria-current={selectedId === run.id ? "true" : undefined}>
      <td className="runs-table__id"><button className="execution-select" type="button" onClick={() => onSelect(run.id)} aria-label={`Abrir execução ${run.id}`}>{run.id}</button></td>
      <td><ExecutionStatusBadge status={run.status} /></td><td>{run.project_id ?? "—"}</td>
      <td>{formatTimestamp(run.started_at)}</td><td>{formatTimestamp(run.finished_at)}</td><td>{formatDuration(run.started_at, run.finished_at)}</td>
      <td>{run.provider_name ?? "—"}</td><td className="runs-table__result">{run.error?.message ?? run.summary ?? "—"}</td>
    </tr>)}</tbody>
  </table></div>;
}
