import type { ProjectLifecycleDto } from "../../lib/api/dtos";

export type ProjectPhase = "PLANNING" | "ARCHITECTURE" | "DEVELOPMENT" | "TESTING" | "DELIVERY";
const phases: readonly Readonly<{ id: ProjectPhase; label: string }>[] = [
  { id: "PLANNING", label: "Planejamento" }, { id: "ARCHITECTURE", label: "Arquitetura" },
  { id: "DEVELOPMENT", label: "Desenvolvimento" }, { id: "TESTING", label: "Testes" },
  { id: "DELIVERY", label: "Entrega" },
];

export function ProjectLifecycle({ projectName, state, loading=false, error=false }: { projectName:string; state:ProjectLifecycleDto|null; loading?:boolean; error?:boolean }) {
  if (loading) return <p role="status">Carregando ciclo de vida...</p>;
  if (error) return <p role="alert">Não foi possível carregar o ciclo de vida.</p>;
  const current = state?.phase ?? "PLANNING";
  const currentIndex = phases.findIndex((phase) => phase.id === current);
  const blocker = state?.phase_status === "blocked" ? state.blocker : null;
  return <section aria-label="Ciclo de vida do projeto"><h3>Projeto: {projectName}</h3>
    <ol>{phases.map((phase, index) => <li key={phase.id} aria-current={index === currentIndex ? "step" : undefined}>{phase.label} {index < currentIndex ? "✓" : index === currentIndex ? "●" : "○"}</li>)}</ol>
    <dl className="execution-facts"><div><dt>Fase atual</dt><dd>{phases[currentIndex].label}</dd></div>{state?.current_sprint?<div><dt>Sprint</dt><dd>{state.current_sprint}</dd></div>:null}<div><dt>Estado</dt><dd>{state?.phase_status ?? "active"}</dd></div>{blocker?<div><dt>Motivo</dt><dd>{blocker}</dd></div>:null}<div><dt>Próxima ação</dt><dd>{state?.next_action ?? "Continuar a fase atual"}</dd></div></dl>
  </section>;
}
