"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ProjectDto } from "../../lib/api/dtos";
import { createProjectsWorkspaceService, type ProjectsWorkspaceService } from "../../lib/services/projectsWorkspace";
import type { ProjectRuntimeWorkspaceService } from "../../lib/services/projectRuntimeWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";
import { ProjectFilesPanel } from "./ProjectFilesPanel";
import type { ProjectWorkspaceService } from "../../lib/services/projectWorkspaceService";

type Props = {
  service?: ProjectsWorkspaceService;
  runtimeService?: ProjectRuntimeWorkspaceService;
  workspaceService?: ProjectWorkspaceService;
  initialContext?: ProjectNavigationContext;
};

export type ProjectNavigationContext = Readonly<{ projectId?: string; sessionId?: string; executionId?: string }>;

export function ProjectsWorkspace({ service, runtimeService, workspaceService, initialContext }: Props) {
  const projects = useMemo(() => service ?? createProjectsWorkspaceService(), [service]);
  const [items, setItems] = useState<readonly ProjectDto[] | null>(null);
  const [listError, setListError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ProjectDto | null>(null);
  const [context, setContext] = useState<ProjectNavigationContext>(() => initialContext ?? readNavigationContext());
  const [contextError, setContextError] = useState(false);
  const [contextAttempt, setContextAttempt] = useState(0);
  const detailsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let current = true;
    projects.list().then(
      (result) => { if (current) { setItems(result); setListError(false); } },
      () => { if (current) { setListError(true); setItems(null); } },
    );
    return () => { current = false; };
  }, [projects, attempt]);

  useEffect(() => {
    if (!context.projectId) return;
    let current = true;
    projects.get(context.projectId).then(
      (project) => { if (current) { setSelected(project); setContextError(false); } },
      () => { if (current) { setSelected(null); setContextError(true); } },
    );
    return () => { current = false; };
  }, [context.projectId, contextAttempt, projects]);

  useEffect(() => {
    const restore = () => setContext(readNavigationContext());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  useEffect(() => {
    if (selected) detailsRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [selected]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!name.trim()) {
      setFormError("Informe o nome do projeto."); return;
    }
    setSubmitting(true); setFormError(null);
    try {
      const created = await projects.create({ name: name.trim() });
      setItems((current) => [...(current ?? []), created]);
      setSelected(created); selectContext({ projectId: created.project_id }); setName("");
    } catch {
      setFormError("Não foi possível criar o projeto. Tente novamente.");
    } finally { setSubmitting(false); }
  }

  function selectContext(next: ProjectNavigationContext) {
    if (sameNavigationContext(context, next)) return;
    setContext(next);
    writeNavigationContext(next);
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Área de trabalho" title="Projetos" description="Crie workspaces isolados para trabalhar com segurança e controle." />
    <Card title="Novo projeto" eyebrow="Criar"><form className="project-form" onSubmit={submit}>
      <label>Nome do projeto<input placeholder="Ex.: API de clientes" value={name} onChange={(event) => setName(event.target.value)} disabled={submitting} /></label>
      {formError ? <p role="alert" className="engineering-form__error">{formError}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? "Criando…" : "Criar projeto"}</Button>
    </form></Card>
    {items === null && !listError ? <div role="status" className="executions-skeleton"><span className="sr-only">Carregando projetos</span></div> : null}
    {listError ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Projetos indisponíveis</h2><Button onClick={() => { setListError(false); setAttempt((value) => value + 1); }}>Tentar novamente</Button></div> : null}
    {contextError ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Contexto do projeto não encontrado</h2><p>Não foi possível reconstruir o projeto informado pela URL.</p><Button onClick={() => { setContextError(false); setContextAttempt((value) => value + 1); }}>Tentar novamente</Button></div> : null}
    {items?.length === 0 ? <div className="dashboard-state"><h2>Nenhum projeto ainda</h2><p>Crie seu primeiro workspace na ASEP.</p></div> : null}
    {items && items.length > 0 ? <Card title="Projetos" eyebrow="Workspaces"><ul className="project-list">{items.map((project) => <li key={project.project_id}><button type="button" onClick={() => { setSelected(project); selectContext({ projectId: project.project_id }); }} aria-pressed={selected?.project_id === project.project_id}><strong>{project.name}</strong><span>{project.workspace_kind === "hosted" ? "Workspace hospedado" : "Workspace local legado"}</span><small>{project.project_id}</small></button></li>)}</ul></Card> : null}
    {selected ? <div ref={detailsRef} className="project-details"><Card title={selected.name} eyebrow="Detalhes do projeto"><dl className="execution-facts"><div><dt>ID do projeto</dt><dd>{selected.project_id}</dd></div><div><dt>Workspace</dt><dd>{selected.workspace_id ?? "Local legado"}</dd></div></dl></Card><ProjectFilesPanel key={selected.project_id} projectId={selected.project_id} service={workspaceService} /><ProjectRuntimePanel key={`runtime-${selected.project_id}`} projectId={selected.project_id} projectName={selected.name} workspaceLabel={selected.workspace_id ?? "Local legado"} service={runtimeService} initialSessionId={context.projectId === selected.project_id ? context.sessionId : undefined} initialExecutionId={context.projectId === selected.project_id ? context.executionId : undefined} onNavigate={(sessionId, executionId) => selectContext({ projectId: selected.project_id, sessionId, executionId })} /></div> : null}
  </div>;
}

function readNavigationContext(): ProjectNavigationContext {
  if (typeof window === "undefined") return {};
  const query = new URLSearchParams(window.location.search);
  return { projectId: query.get("project_id") || undefined, sessionId: query.get("session_id") || undefined, executionId: query.get("execution_id") || undefined };
}

function writeNavigationContext(context: ProjectNavigationContext) {
  if (typeof window === "undefined") return;
  const query = new URLSearchParams();
  if (context.projectId) query.set("project_id", context.projectId);
  if (context.sessionId) query.set("session_id", context.sessionId);
  if (context.executionId) query.set("execution_id", context.executionId);
  window.history.pushState(null, "", `${window.location.pathname}${query.size ? `?${query}` : ""}`);
}

function sameNavigationContext(
  current: ProjectNavigationContext,
  next: ProjectNavigationContext,
) {
  return current.projectId === next.projectId
    && current.sessionId === next.sessionId
    && current.executionId === next.executionId;
}
