"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ProjectDto } from "../../lib/api/dtos";
import { createProjectsWorkspaceService, type ProjectsWorkspaceService } from "../../lib/services/projectsWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";
import { ProjectRuntimePanel } from "./ProjectRuntimePanel";

export function ProjectsWorkspace({ service }: { service?: ProjectsWorkspaceService }) {
  const projects = useMemo(() => service ?? createProjectsWorkspaceService(), [service]);
  const [items, setItems] = useState<readonly ProjectDto[] | null>(null);
  const [listError, setListError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ProjectDto | null>(null);

  useEffect(() => {
    let current = true;
    projects.list().then(
      (result) => { if (current) { setItems(result); setListError(false); } },
      () => { if (current) { setListError(true); setItems(null); } },
    );
    return () => { current = false; };
  }, [projects, attempt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!name.trim() || !workspace.trim()) {
      setFormError("Project name and workspace path are required."); return;
    }
    setSubmitting(true); setFormError(null);
    try {
      const created = await projects.create({ name: name.trim(), workspace_path: workspace.trim() });
      setItems((current) => [...(current ?? []), created]);
      setSelected(created); setName(""); setWorkspace("");
    } catch {
      setFormError("Project could not be created. Review the workspace and try again.");
    } finally { setSubmitting(false); }
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Workspace" title="Projects" description="Register explicit local workspaces for controlled engineering operations." />
    <Card title="New project" eyebrow="Create"><form className="project-form" onSubmit={submit}>
      <label>Project name<input value={name} onChange={(event) => setName(event.target.value)} disabled={submitting} /></label>
      <label>Workspace path<input value={workspace} onChange={(event) => setWorkspace(event.target.value)} disabled={submitting} /></label>
      {formError ? <p role="alert" className="engineering-form__error">{formError}</p> : null}
      <Button type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create Project"}</Button>
    </form></Card>
    {items === null && !listError ? <div role="status" className="executions-skeleton"><span className="sr-only">Loading projects</span></div> : null}
    {listError ? <div role="alert" className="dashboard-state dashboard-state--error"><h2>Projects unavailable</h2><Button onClick={() => { setListError(false); setAttempt((value) => value + 1); }}>Try again</Button></div> : null}
    {items?.length === 0 ? <div className="dashboard-state"><h2>No projects yet</h2><p>Create a project to associate a local workspace.</p></div> : null}
    {items && items.length > 0 ? <Card title="Projects" eyebrow="Workspaces"><ul className="project-list">{items.map((project) => <li key={project.project_id}><button type="button" onClick={() => setSelected(project)}><strong>{project.name}</strong><span>{project.workspace_path}</span><small>{project.project_id}</small></button></li>)}</ul></Card> : null}
    {selected ? <><Card title={selected.name} eyebrow="Project details"><dl className="execution-facts"><div><dt>Project ID</dt><dd>{selected.project_id}</dd></div><div><dt>Workspace</dt><dd>{selected.workspace_path}</dd></div></dl></Card><ProjectRuntimePanel projectId={selected.project_id} /></> : null}
  </div>;
}
