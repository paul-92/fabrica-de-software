import type { IntelligentEngineeringResponseDto } from "../../lib/api/dtos";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";
import { formatExecutionStatus } from "../../lib/presentation";

function List({ items, empty }: { items: readonly string[]; empty: string }) {
  return items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{empty}</p>;
}

export function PlanningResult({ result }: { result: IntelligentEngineeringResponseDto["planning_result"] }) {
  return <Card title={result.plan.goal} eyebrow="Resultado do planejamento">
    <div className="engineering-statistics">
      <div><strong>{result.statistics.total_steps}</strong><span>Etapas</span></div>
      <div><strong>{result.statistics.memory_entries_considered}</strong><span>Memórias</span></div>
      <div><strong>{result.statistics.dependency_count}</strong><span>Dependências</span></div>
    </div>
    <ol className="engineering-steps">{result.plan.steps.map((step) => <li key={step.step_id}><strong>{step.description}</strong><span>{step.status} · {step.required_capability}</span></li>)}</ol>
    {result.warnings.length ? <><h3>Avisos</h3><List items={result.warnings} empty="Nenhum aviso." /></> : null}
  </Card>;
}

export function RepairResult({ result }: { result: IntelligentEngineeringResponseDto["engineering_result"] }) {
  return <Card title={result.proposal.summary} eyebrow="Resultado da engenharia" action={<StatusBadge status={result.repair_result.status === "succeeded" ? "success" : "warning"}>{formatExecutionStatus(result.repair_result.status)}</StatusBadge>}>
    <p>{result.proposal.reasoning}</p>
    <p>Confiança da proposta: {Math.round(result.proposal.confidence * 100)}%</p>
    <h3>Arquivos candidatos</h3><List items={result.proposal.candidate_files} empty="Nenhum arquivo candidato." />
    <h3>Ações sugeridas</h3><List items={result.proposal.suggested_actions} empty="Nenhuma ação sugerida." />
    <h3>Alterações do reparo</h3>
    {result.plan.changes.length ? <ul>{result.plan.changes.map((change) => <li key={change.path}><strong>{change.path}</strong> — {change.reason}</li>)}</ul> : <p>Nenhuma alteração de reparo.</p>}
    <h3>Mensagens</h3><List items={result.repair_result.messages} empty="Nenhuma mensagem de reparo." />
  </Card>;
}

export function ReflectionResult({ reflection }: { reflection: IntelligentEngineeringResponseDto["engineering_result"]["reflection"] }) {
  return <Card title={reflection.summary} eyebrow="Reflexão">
    <p>Resultado: {reflection.outcome}</p><p>Confiança: {Math.round(reflection.confidence * 100)}%</p>
    <p>Nova tentativa recomendada: {reflection.should_retry ? "Sim" : "Não"}</p>
    <h3>Aprendizados</h3><List items={reflection.lessons} empty="Nenhum aprendizado registrado." />
    <h3>Ações recomendadas</h3><List items={reflection.recommended_actions} empty="Nenhuma ação recomendada." />
  </Card>;
}

export function EngineeringResult({ response }: { response: IntelligentEngineeringResponseDto }) {
  return <section className="engineering-results" aria-labelledby="engineering-results-title">
    <h2 id="engineering-results-title">Resultado da execução</h2>
    <PlanningResult result={response.planning_result} />
    <RepairResult result={response.engineering_result} />
    <ReflectionResult reflection={response.engineering_result.reflection} />
  </section>;
}
