import type { IntelligentEngineeringResponseDto } from "../../lib/api/dtos";
import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";

function List({ items, empty }: { items: readonly string[]; empty: string }) {
  return items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{empty}</p>;
}

export function PlanningResult({ result }: { result: IntelligentEngineeringResponseDto["planning_result"] }) {
  return <Card title={result.plan.goal} eyebrow="Planning result">
    <div className="engineering-statistics">
      <div><strong>{result.statistics.total_steps}</strong><span>Steps</span></div>
      <div><strong>{result.statistics.memory_entries_considered}</strong><span>Memory entries</span></div>
      <div><strong>{result.statistics.dependency_count}</strong><span>Dependencies</span></div>
    </div>
    <ol className="engineering-steps">{result.plan.steps.map((step) => <li key={step.step_id}><strong>{step.description}</strong><span>{step.status} · {step.required_capability}</span></li>)}</ol>
    {result.warnings.length ? <><h3>Warnings</h3><List items={result.warnings} empty="No warnings." /></> : null}
  </Card>;
}

export function RepairResult({ result }: { result: IntelligentEngineeringResponseDto["engineering_result"] }) {
  return <Card title={result.proposal.summary} eyebrow="Engineering result" action={<StatusBadge status={result.repair_result.status === "succeeded" ? "success" : "warning"}>{result.repair_result.status}</StatusBadge>}>
    <p>{result.proposal.reasoning}</p>
    <p>Proposal confidence: {Math.round(result.proposal.confidence * 100)}%</p>
    <h3>Candidate files</h3><List items={result.proposal.candidate_files} empty="No candidate files." />
    <h3>Suggested actions</h3><List items={result.proposal.suggested_actions} empty="No suggested actions." />
    <h3>Repair changes</h3>
    {result.plan.changes.length ? <ul>{result.plan.changes.map((change) => <li key={change.path}><strong>{change.path}</strong> — {change.reason}</li>)}</ul> : <p>No repair changes.</p>}
    <h3>Messages</h3><List items={result.repair_result.messages} empty="No repair messages." />
  </Card>;
}

export function ReflectionResult({ reflection }: { reflection: IntelligentEngineeringResponseDto["engineering_result"]["reflection"] }) {
  return <Card title={reflection.summary} eyebrow="Reflection">
    <p>Outcome: {reflection.outcome}</p><p>Confidence: {Math.round(reflection.confidence * 100)}%</p>
    <p>Retry recommended: {reflection.should_retry ? "Yes" : "No"}</p>
    <h3>Lessons</h3><List items={reflection.lessons} empty="No lessons recorded." />
    <h3>Recommended actions</h3><List items={reflection.recommended_actions} empty="No recommended actions." />
  </Card>;
}

export function EngineeringResult({ response }: { response: IntelligentEngineeringResponseDto }) {
  return <section className="engineering-results" aria-labelledby="engineering-results-title">
    <h2 id="engineering-results-title">Execution result</h2>
    <PlanningResult result={response.planning_result} />
    <RepairResult result={response.engineering_result} />
    <ReflectionResult reflection={response.engineering_result.reflection} />
  </section>;
}
