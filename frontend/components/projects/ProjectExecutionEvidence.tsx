import type {
  ProjectEngineeringEvidenceDto,
  WorkspaceChangeDto,
} from "../../lib/api/dtos";
import {
  formatExecutionStatus,
  formatWorkspaceChange,
} from "../../lib/presentation";

type Props = Readonly<{
  evidence: ProjectEngineeringEvidenceDto & { execution_id: string };
  changes: readonly WorkspaceChangeDto[];
  output: string | null;
}>;

export function ProjectExecutionEvidence({ evidence, changes, output }: Props) {
  const validations = [...(evidence.validations ?? [])].sort(
    (left, right) => left.sequence - right.sequence,
  );
  const steps = evidence.step_results ?? [];

  return <section aria-label="Evidências da execução de engenharia">
    <h3>Resultado da execução</h3>
    <dl className="execution-facts">
      <div><dt>Execution ID</dt><dd><code>{evidence.execution_id}</code></dd></div>
      <div><dt>Status</dt><dd>{evidence.status ? formatExecutionStatus(evidence.status) : "Concluído"}</dd></div>
    </dl>

    {evidence.operational_plan ? <>
      <h4>Plano operacional</h4>
      <ol>{evidence.operational_plan.steps.map((step) => <li key={step.step_id}>
        <strong>{step.description}</strong>
        <small>Operação: {step.operation}</small>
      </li>)}</ol>
    </> : null}

    {steps.length > 0 ? <>
      <h4>Etapas executadas</h4>
      <ol>{steps.map((step) => <li key={step.step_id}>
        <strong>{step.succeeded ? "Concluída" : "Falhou"}: {step.step_id}</strong>
        <dl className="execution-facts">
          <div><dt>Executor</dt><dd>{step.executor}</dd></div>
          <div><dt>Tool</dt><dd>{step.tool_id}</dd></div>
        </dl>
        {step.output ? <pre>{step.output}</pre> : null}
      </li>)}</ol>
    </> : null}

    <h4>Arquivos alterados</h4>
    {changes.length > 0 ? <ul>{changes.map((change) => <li key={`${change.change_type}:${change.path}`}>
      <strong>{formatWorkspaceChange(change.change_type)}</strong> {change.path}
    </li>)}</ul> : <p>Nenhuma alteração detectada no projeto.</p>}

    {validations.length > 0 ? <>
      <h4>Validações</h4>
      {validations.map((validation) => <article key={validation.sequence}>
        <h5>#{validation.sequence} · {validation.validator}</h5>
        <dl className="execution-facts">
          <div><dt>Comando</dt><dd><code>{validation.command.join(" ")}</code></dd></div>
          <div><dt>Exit code</dt><dd>{validation.exit_code}</dd></div>
          <div><dt>Status</dt><dd>{validation.status === "passed" ? "Aprovada" : "Falhou"}</dd></div>
        </dl>
        <pre>{validation.output}</pre>
      </article>)}
    </> : null}

    {evidence.repair ? <>
      <h4>Repair</h4>
      <p>{evidence.repair.attempt_count} tentativa(s) · {formatRepairOutcome(evidence.repair.outcome)}</p>
    </> : null}

    {evidence.quality_gate ? <>
      <h4>Quality Gate</h4>
      <p><strong>{formatGateDecision(evidence.quality_gate.decision)}</strong></p>
      <Criteria title="Critérios atendidos" items={evidence.quality_gate.satisfied_criteria} empty="Nenhum critério atendido registrado." />
      <Criteria title="Critérios não atendidos" items={evidence.quality_gate.unsatisfied_criteria} empty="Nenhum critério não atendido." />
    </> : null}

    <h4>Resultado final</h4>
    <pre>{output ?? "Nenhum resultado disponível."}</pre>
    {evidence.error_code ? <p role="alert"><strong>Erro:</strong> {evidence.error_code}</p> : null}
  </section>;
}

function Criteria({ title, items, empty }: { title: string; items: readonly string[]; empty: string }) {
  return <section aria-label={title}><h5>{title}</h5>{items.length > 0 ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{empty}</p>}</section>;
}

function formatRepairOutcome(outcome: "succeeded" | "failed" | "exhausted"): string {
  return { succeeded: "Concluído", failed: "Falhou", exhausted: "Tentativas esgotadas" }[outcome];
}

function formatGateDecision(decision: "APPROVED" | "APPROVED_WITH_PENDING" | "BLOCKED"): string {
  return { APPROVED: "Aprovado", APPROVED_WITH_PENDING: "Aprovado com pendências", BLOCKED: "Bloqueado" }[decision];
}
