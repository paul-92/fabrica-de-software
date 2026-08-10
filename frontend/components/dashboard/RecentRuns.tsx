import type { RunDto } from "../../lib/api/dtos";
import { Card } from "../Card";
import { RunStatusBadge } from "./RunStatusBadge";

function formatDate(value: string | null) {
  if (value === null) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function RecentRuns({ runs }: { runs: readonly RunDto[] }) {
  return (
    <Card title="Execuções recentes" eyebrow="Atividade">
      <div className="runs-table-wrap">
        <table className="runs-table">
          <thead>
            <tr>
              <th scope="col">Execução</th>
              <th scope="col">Status</th>
              <th scope="col">Projeto</th>
              <th scope="col">Início</th>
              <th scope="col">Fim</th>
              <th scope="col">Provedor</th>
              <th scope="col">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="runs-table__id">{run.id}</td>
                <td><RunStatusBadge status={run.status} /></td>
                <td>{run.project_id ?? "—"}</td>
                <td>{formatDate(run.started_at)}</td>
                <td>{formatDate(run.finished_at)}</td>
                <td>{run.provider_name ?? "—"}</td>
                <td className="runs-table__result">
                  {run.error?.message ?? run.summary ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
