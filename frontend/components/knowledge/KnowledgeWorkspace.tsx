"use client";

import { useEffect, useMemo, useState } from "react";
import type { ProjectDto, ProjectSessionDto, SessionMemoryDto } from "../../lib/api/dtos";
import { formatMemoryKind } from "../../lib/presentation";
import { createKnowledgeLoader, type KnowledgeLoader } from "../../lib/services/knowledge";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";

export function KnowledgeWorkspace({ loader }: { loader?: KnowledgeLoader }) {
  const api = useMemo(() => loader ?? createKnowledgeLoader(), [loader]);
  const [projects, setProjects] = useState<readonly ProjectDto[] | null>(null);
  const [projectsError, setProjectsError] = useState(false);
  const [projectsAttempt, setProjectsAttempt] = useState(0);
  const [selectedProject, setSelectedProject] = useState<ProjectDto | null>(null);
  const [sessions, setSessions] = useState<readonly ProjectSessionDto[] | null>(null);
  const [sessionsError, setSessionsError] = useState(false);
  const [sessionsAttempt, setSessionsAttempt] = useState(0);
  const [selectedSession, setSelectedSession] = useState<ProjectSessionDto | null>(null);
  const [memory, setMemory] = useState<readonly SessionMemoryDto[] | null>(null);
  const [memoryError, setMemoryError] = useState(false);
  const [memoryAttempt, setMemoryAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    api.listProjects().then(
      (items) => { if (current) { setProjects(items); setProjectsError(false); } },
      () => { if (current) { setProjects([]); setProjectsError(true); } },
    );
    return () => { current = false; };
  }, [api, projectsAttempt]);

  useEffect(() => {
    if (!selectedProject) return;
    let current = true;
    api.listSessions(selectedProject.project_id).then(
      (items) => { if (current) { setSessions(items); setSessionsError(false); } },
      () => { if (current) { setSessions([]); setSessionsError(true); } },
    );
    return () => { current = false; };
  }, [api, selectedProject, sessionsAttempt]);

  useEffect(() => {
    if (!selectedProject || !selectedSession) return;
    let current = true;
    api.listMemory(selectedProject.project_id, selectedSession.session_id).then(
      (items) => { if (current) { setMemory(items); setMemoryError(false); } },
      () => { if (current) { setMemory([]); setMemoryError(true); } },
    );
    return () => { current = false; };
  }, [api, selectedProject, selectedSession, memoryAttempt]);

  function chooseProject(project: ProjectDto) {
    setSelectedProject(project);
    setSessions(null); setSessionsError(false);
    setSelectedSession(null); setMemory(null); setMemoryError(false);
  }

  function chooseSession(session: ProjectSessionDto) {
    setSelectedSession(session);
    setMemory(null); setMemoryError(false);
  }

  function retryProjects() {
    setProjects(null); setProjectsError(false);
    setSelectedProject(null); setSessions(null); setSelectedSession(null); setMemory(null);
    setProjectsAttempt((value) => value + 1);
  }

  function retrySessions() {
    setSessions(null); setSessionsError(false); setSelectedSession(null); setMemory(null); setMemoryError(false);
    setSessionsAttempt((value) => value + 1);
  }

  function retryMemory() {
    setMemory(null); setMemoryError(false);
    setMemoryAttempt((value) => value + 1);
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Aprendizado" title="Conhecimento" description="Explore memórias duráveis organizadas por projeto e sessão." />
    {projects === null ? <Loading label="Carregando projetos" /> : projectsError ? <ErrorState title="Projetos indisponíveis" message="Não foi possível carregar os projetos." retry={retryProjects} /> : projects.length === 0 ? <EmptyState title="Nenhum projeto ainda" message="Crie um projeto para começar a registrar conhecimento por sessão." /> : <ProjectList projects={projects} selected={selectedProject} choose={chooseProject} />}
    {selectedProject ? <Card title="Sessões" eyebrow={selectedProject.name}>
      {sessions === null ? <Loading label="Carregando sessões" /> : sessionsError ? <ErrorState title="Sessões indisponíveis" message="Não foi possível carregar as sessões deste projeto." retry={retrySessions} /> : sessions.length === 0 ? <p>Nenhuma sessão neste projeto.</p> : <ul className="knowledge-selection-list">{sessions.map((session) => <li key={session.session_id}><button type="button" aria-pressed={selectedSession?.session_id === session.session_id} onClick={() => chooseSession(session)}><strong>{session.title}</strong><span>{formatDate(session.updated_at)}</span></button></li>)}</ul>}
    </Card> : projects && projects.length > 0 ? <EmptyState title="Selecione um projeto" message="Escolha um projeto para consultar suas sessões." /> : null}
    {selectedSession ? <Card title="Memórias da sessão" eyebrow={selectedSession.title}>
      {memory === null ? <Loading label="Carregando memórias" /> : memoryError ? <ErrorState title="Memórias indisponíveis" message="Não foi possível carregar as memórias desta sessão." retry={retryMemory} /> : memory.length === 0 ? <p>Nenhuma memória nesta sessão.</p> : <MemoryList items={memory} />}
    </Card> : selectedProject && sessions && sessions.length > 0 ? <EmptyState title="Selecione uma sessão" message="Escolha uma sessão para consultar suas memórias." /> : null}
  </div>;
}

function ProjectList({ projects, selected, choose }: { projects: readonly ProjectDto[]; selected: ProjectDto | null; choose(project: ProjectDto): void }) {
  return <Card title="Projetos" eyebrow="Memória disponível"><ul className="knowledge-selection-list">{projects.map((project) => <li key={project.project_id}><button type="button" aria-pressed={selected?.project_id === project.project_id} onClick={() => choose(project)}><strong>{project.name}</strong><span>{project.project_id}</span></button></li>)}</ul></Card>;
}

function MemoryList({ items }: { items: readonly SessionMemoryDto[] }) {
  return <ul className="knowledge-memory-list">{items.map((entry) => <li key={entry.memory_id}><header><strong>{formatMemoryKind(entry.kind)}</strong><time dateTime={entry.created_at}>{formatDate(entry.created_at)}</time></header><p>{entry.content}</p><small>{entry.source_execution_id ? `Execução ${entry.source_execution_id}` : "Origem manual"}</small></li>)}</ul>;
}

function Loading({ label }: { label: string }) {
  return <p role="status">{label}...</p>;
}

function ErrorState({ title, message, retry }: { title: string; message: string; retry(): void }) {
  return <div role="alert" className="knowledge-inline-state"><strong>{title}</strong><p>{message}</p><Button onClick={retry}>Tentar novamente</Button></div>;
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="knowledge-inline-state"><strong>{title}</strong><p>{message}</p></div>;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
