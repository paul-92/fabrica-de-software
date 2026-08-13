import type {
  ProjectEngineeringEvidenceDto,
  WorkspaceChangeDto,
} from "../../lib/api/dtos";
import {
  formatExecutionStatus,
  formatWorkspaceChange,
} from "../../lib/presentation";
import { StatusBadge } from "../StatusBadge";

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
    {evidence.status ? <p role="status">Fase persistida: {persistedPhase(evidence.status)}</p> : null}

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

    {(validations.length > 0 || evidence.repair || evidence.quality_gate) ? <QualityEvidence evidence={evidence} validations={validations} /> : null}

    <h4>Resultado final</h4>
    <pre>{output ?? "Nenhum resultado disponível."}</pre>
    {evidence.error_code ? <p role="alert"><strong>Erro:</strong> {evidence.error_code}</p> : null}
  </section>;
}

type Validation = NonNullable<ProjectEngineeringEvidenceDto["validations"]>[number];
const TEST_VALIDATORS = new Set(["pytest", "vitest"]);
const CHECK_VALIDATORS = new Set(["compileall", "typecheck", "eslint", "next_build"]);
const VALIDATOR_NAMES: Readonly<Record<string, string>> = {
  pytest: "Testes Python",
  vitest: "Testes Vitest",
  compileall: "Compilação Python",
  typecheck: "TypeScript typecheck",
  eslint: "ESLint",
  next_build: "Next.js production build",
};

function QualityEvidence({ evidence, validations }: { evidence: ProjectEngineeringEvidenceDto; validations: readonly Validation[] }) {
  const passed = validations.filter((item) => item.status === "passed").length;
  const failed = validations.length - passed;
  const tests = validations.filter((item) => TEST_VALIDATORS.has(item.validator));
  const checks = validations.filter((item) => CHECK_VALIDATORS.has(item.validator));
  const other = validations.filter((item) => !TEST_VALIDATORS.has(item.validator) && !CHECK_VALIDATORS.has(item.validator));
  return <section className="engineering-quality" aria-labelledby="engineering-quality-title">
    <h4 id="engineering-quality-title">Qualidade</h4>
    <dl className="quality-summary" aria-label="Resumo de qualidade">
      <div><dt>Validações</dt><dd>{validations.length}</dd></div>
      <div><dt>PASS</dt><dd>{passed}</dd></div>
      <div><dt>FAIL</dt><dd>{failed}</dd></div>
      <div><dt>Repairs</dt><dd>{evidence.repair?.attempt_count ?? 0}</dd></div>
      <div><dt>Quality Gate</dt><dd>{evidence.quality_gate ? formatGateDecision(evidence.quality_gate.decision) : "Não registrado"}</dd></div>
    </dl>
    <ValidationGroup title="Testes" validations={tests} />
    <ValidationGroup title="Checks" validations={checks} />
    {other.length > 0 ? <ValidationGroup title="Outras validações" validations={other} /> : null}
    {evidence.repair ? <RepairFlow repair={evidence.repair} validations={validations} /> : null}
    {evidence.quality_gate ? <section className="quality-gate" aria-labelledby="quality-gate-title">
      <h5 id="quality-gate-title">Quality Gate</h5>
      <StatusBadge status={evidence.quality_gate.decision === "BLOCKED" ? "danger" : "success"}>{evidence.quality_gate.decision}</StatusBadge>
      <p>{formatGateDecision(evidence.quality_gate.decision)}</p>
      <div className="quality-gate__criteria">
        <Criteria title="Critérios atendidos" items={evidence.quality_gate.satisfied_criteria} empty="Nenhum critério atendido registrado." />
        <Criteria title="Critérios não atendidos" items={evidence.quality_gate.unsatisfied_criteria} empty="Nenhum critério não atendido." />
      </div>
    </section> : null}
  </section>;
}

function ValidationGroup({ title, validations }: { title: string; validations: readonly Validation[] }) {
  return <section className="validation-group" aria-label={title}><h5>{title}</h5>{validations.length === 0 ? <p>Nenhum registro.</p> : <ol>{validations.map((validation) => <li key={validation.sequence} className="validation-result">
    <header><span><strong>{VALIDATOR_NAMES[validation.validator] ?? validation.validator}</strong> <code>{validation.validator}</code></span><StatusBadge status={validation.status === "passed" ? "success" : "danger"}>{validation.status === "passed" ? "PASS" : "FAIL"}</StatusBadge></header>
    <p>Execução #{validation.sequence} · exit code {validation.exit_code}</p>
    <details><summary>Ver comando e output</summary>{validation.command.length > 0 ? <p><strong>Comando:</strong> <code>{validation.command.join(" ")}</code></p> : null}<pre>{validation.output}</pre></details>
  </li>)}</ol>}</section>;
}

function RepairFlow({ repair, validations }: { repair: NonNullable<ProjectEngineeringEvidenceDto["repair"]>; validations: readonly Validation[] }) {
  const transitions = validations.flatMap((failed, index) => {
    if (failed.status !== "failed") return [];
    const revalidation = validations.slice(index + 1).find((item) => item.validator === failed.validator);
    return revalidation ? [{ validator: failed.validator, status: revalidation.status }] : [];
  });
  return <section className="repair-flow" aria-labelledby="repair-flow-title"><h5 id="repair-flow-title">Repair e revalidation</h5><p>{repair.attempt_count} tentativa(s) · {formatRepairOutcome(repair.outcome)}</p>{transitions.length > 0 ? <ul>{transitions.map((item, index) => <li key={`${item.validator}:${index}`}><strong>{item.validator}</strong>: FAIL → repair → {item.status === "passed" ? "PASS" : "FAIL"}</li>)}</ul> : <p>Não há vínculo individual de revalidation registrado nas evidências.</p>}</section>;
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

function persistedPhase(status: "pending" | "running" | "succeeded" | "failed"): string {
  return { pending: "Aguardando aprovação", running: "Em execução", succeeded: "Finalizada com sucesso", failed: "Finalizada com falha" }[status];
}
