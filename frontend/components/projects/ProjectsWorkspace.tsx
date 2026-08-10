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
};

export function ProjectsWorkspace({ service, runtimeService, workspaceService }: Props) {
  const projects = useMemo(() => service ?? createProjectsWorkspaceService(), [service]);
  const [items, setItems] = useState<readonly ProjectDto[] | null>(null);
  const [listError, setListError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ProjectDto | null>(null);
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
    if (selected) detailsRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [selected]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!name.trim() || !workspace.trim()) {
      setFormError("Informe o nome e a pasta do projeto."); return;
    }
    setSubmitting(true); setFormError(null);
    try {
      const created = await projects.create({ name: name.trim(), workspace_path: workspace.trim() });
      setItems((current) => [...(current ?? []), created]);
      setSelected(created); setName(""); setWorkspace("");
    } catch {
      setFormError("Não foi possível criar o projeto. Revise a pasta informada e tente novamente.");
    } finally { setSubmitting(false); }
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Área de trabalho" title="Projetos" description="Conecte pastas locais para trabalhar com segurança e controle." />
    <Card title="Novo projeto" eyebrow="Criar"><form className="project-form" onSubmit={submit}>
      <label>Nome do projeto<input placeholder="Ex.: API de clientes" value={name} onChange={(event) => setName(event.target.value)} disabled={submitting} /></label>
      <label>Pasta do projeto<input placeholder="Ex.: C:\\projetos\\clientes" value={workspace} onChange={(event) => setWorkspace(event.target.value)} disabled={submitting} /></label>
      {formError ? <p role="alert" className="engineering-form__error">{formError}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? "Criando…" : "Criar projeto"}</Button>
    </form></Card>
    {items === null && !listError ? <div role="status" className="executions-skeleton"><span className="sr-only">Carregando projetos</span></div> : null}
    {listError ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Projetos indisponíveis</h2><Button onClick={() => { setListError(false); setAttempt((value) => value + 1); }}>Tentar novamente</Button></div> : null}
    {items?.length === 0 ? <div className="dashboard-state"><h2>Nenhum projeto ainda</h2><p>Crie seu primeiro projeto para conectar uma pasta local à ASEP.</p></div> : null}
    {items && items.length > 0 ? <Card title="Projetos" eyebrow="Pastas locais"><ul className="project-list">{items.map((project) => <li key={project.project_id}><button type="button" onClick={() => setSelected(project)} aria-pressed={selected?.project_id === project.project_id}><strong>{project.name}</strong><span>{project.workspace_path}</span><small>{project.project_id}</small></button></li>)}</ul></Card> : null}
    {selected ? <div ref={detailsRef} className="project-details"><Card title={selected.name} eyebrow="Detalhes do projeto"><dl className="execution-facts"><div><dt>ID do projeto</dt><dd>{selected.project_id}</dd></div><div><dt>Pasta</dt><dd>{selected.workspace_path}</dd></div></dl></Card><ProjectFilesPanel key={selected.project_id} projectId={selected.project_id} service={workspaceService} /><ProjectRuntimePanel projectId={selected.project_id} projectName={selected.name} workspacePath={selected.workspace_path} service={runtimeService} /></div> : null}
  </div>;
}
