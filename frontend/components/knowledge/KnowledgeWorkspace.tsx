"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import type { ProjectDto, ProjectSessionDto, SessionMemoryDto, SessionMemoryKind, SessionMemoryOrder, SessionMemorySearchParams } from "../../lib/api/dtos";
import { formatMemoryKind } from "../../lib/presentation";
import { createKnowledgeLoader, type KnowledgeLoader } from "../../lib/services/knowledge";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";

const PAGE_SIZE = 25;
const DEFAULT_FILTERS: SessionMemorySearchParams = { order: "newest", page_size: PAGE_SIZE };

export function KnowledgeWorkspace({ loader }: { loader?: KnowledgeLoader }) {
  const api = useMemo(() => loader ?? createKnowledgeLoader(), [loader]);
  const requestVersion = useRef(0);
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
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState(false);
  const [text, setText] = useState("");
  const [kind, setKind] = useState<SessionMemoryKind | "">("");
  const [order, setOrder] = useState<SessionMemoryOrder>("newest");
  const [filters, setFilters] = useState<SessionMemorySearchParams>(DEFAULT_FILTERS);

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
    const version = ++requestVersion.current;
    api.searchMemory(selectedProject.project_id, selectedSession.session_id, filters).then(
      (page) => {
        if (version !== requestVersion.current) return;
        setMemory(page.items); setNextCursor(page.next_cursor); setMemoryError(false);
      },
      () => {
        if (version !== requestVersion.current) return;
        setMemory([]); setNextCursor(null); setMemoryError(true);
      },
    );
  }, [api, selectedProject, selectedSession, filters, memoryAttempt]);

  function resetMemoryState() {
    requestVersion.current += 1;
    setMemory(null); setMemoryError(false); setNextCursor(null);
    setLoadingMore(false); setLoadMoreError(false);
  }

  function chooseProject(project: ProjectDto) {
    requestVersion.current += 1;
    setSelectedProject(project);
    setSessions(null); setSessionsError(false); setSelectedSession(null);
    setMemory(null); setMemoryError(false); setNextCursor(null);
    setLoadingMore(false); setLoadMoreError(false);
    setText(""); setKind(""); setOrder("newest"); setFilters(DEFAULT_FILTERS);
  }

  function chooseSession(session: ProjectSessionDto) {
    requestVersion.current += 1;
    setSelectedSession(session);
    setText(""); setKind(""); setOrder("newest"); setFilters(DEFAULT_FILTERS);
    resetMemoryState();
  }

  function retryProjects() {
    requestVersion.current += 1;
    setProjects(null); setProjectsError(false); setSelectedProject(null);
    setSessions(null); setSelectedSession(null); setMemory(null);
    setProjectsAttempt((value) => value + 1);
  }

  function retrySessions() {
    requestVersion.current += 1;
    setSessions(null); setSessionsError(false); setSelectedSession(null);
    setMemory(null); setMemoryError(false);
    setSessionsAttempt((value) => value + 1);
  }

  function retryMemory() {
    resetMemoryState();
    setMemoryAttempt((value) => value + 1);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetMemoryState();
    const meaningfulText = text.trim();
    setFilters({
      ...(meaningfulText ? { text: meaningfulText } : {}),
      ...(kind ? { kind } : {}),
      order,
      page_size: PAGE_SIZE,
    });
  }

  function loadMore() {
    if (!selectedProject || !selectedSession || !nextCursor || loadingMore) return;
    const version = ++requestVersion.current;
    setLoadingMore(true); setLoadMoreError(false);
    api.searchMemory(selectedProject.project_id, selectedSession.session_id, {
      ...filters,
      cursor: nextCursor,
    }).then(
      (page) => {
        if (version !== requestVersion.current) return;
        setMemory((current) => appendUnique(current ?? [], page.items));
        setNextCursor(page.next_cursor); setLoadingMore(false); setLoadMoreError(false);
      },
      () => {
        if (version !== requestVersion.current) return;
        setLoadingMore(false); setLoadMoreError(true);
      },
    );
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Aprendizado" title="Conhecimento" description="Explore memórias duráveis organizadas por projeto e sessão." />
    {projects === null ? <Loading label="Carregando projetos" /> : projectsError ? <ErrorState title="Projetos indisponíveis" message="Não foi possível carregar os projetos." retry={retryProjects} /> : projects.length === 0 ? <EmptyState title="Nenhum projeto ainda" message="Crie um projeto para começar a registrar conhecimento por sessão." /> : <ProjectList projects={projects} selected={selectedProject} choose={chooseProject} />}
    {selectedProject ? <Card title="Sessões" eyebrow={selectedProject.name}>
      {sessions === null ? <Loading label="Carregando sessões" /> : sessionsError ? <ErrorState title="Sessões indisponíveis" message="Não foi possível carregar as sessões deste projeto." retry={retrySessions} /> : sessions.length === 0 ? <p>Nenhuma sessão neste projeto.</p> : <ul className="knowledge-selection-list">{sessions.map((session) => <li key={session.session_id}><button type="button" aria-pressed={selectedSession?.session_id === session.session_id} onClick={() => chooseSession(session)}><strong>{session.title}</strong><span>{formatDate(session.updated_at)}</span></button></li>)}</ul>}
    </Card> : projects && projects.length > 0 ? <EmptyState title="Selecione um projeto" message="Escolha um projeto para consultar suas sessões." /> : null}
    {selectedSession ? <Card title="Memórias da sessão" eyebrow={selectedSession.title}>
      <SearchForm text={text} kind={kind} order={order} setText={setText} setKind={setKind} setOrder={setOrder} submit={submitSearch} />
      {memory === null ? <Loading label="Carregando memórias" /> : memoryError ? <ErrorState title="Memórias indisponíveis" message="Não foi possível carregar as memórias desta sessão." retry={retryMemory} /> : memory.length === 0 ? <EmptyState title="Nenhuma memória encontrada" message="A sessão não possui memórias correspondentes aos filtros." /> : <>
        <MemoryList items={memory} />
        {nextCursor ? <div className="knowledge-load-more"><Button type="button" variant="secondary" disabled={loadingMore} onClick={loadMore}>{loadingMore ? "Carregando mais..." : "Carregar mais"}</Button></div> : null}
        {loadMoreError ? <ErrorState title="Não foi possível carregar mais" message="Os resultados atuais foram preservados." retry={loadMore} retryLabel="Tentar carregar mais" /> : null}
      </>}
    </Card> : selectedProject && sessions && sessions.length > 0 ? <EmptyState title="Selecione uma sessão" message="Escolha uma sessão para consultar suas memórias." /> : null}
  </div>;
}

function SearchForm({ text, kind, order, setText, setKind, setOrder, submit }: { text: string; kind: SessionMemoryKind | ""; order: SessionMemoryOrder; setText(value: string): void; setKind(value: SessionMemoryKind | ""): void; setOrder(value: SessionMemoryOrder): void; submit(event: FormEvent<HTMLFormElement>): void }) {
  return <form className="knowledge-search-form" onSubmit={submit}>
    <label htmlFor="knowledge-search-text">Buscar nas memórias<input id="knowledge-search-text" type="search" value={text} onChange={(event) => setText(event.target.value)} /></label>
    <label htmlFor="knowledge-search-kind">Tipo<select id="knowledge-search-kind" value={kind} onChange={(event) => setKind(event.target.value as SessionMemoryKind | "")}><option value="">Todos</option><option value="decision">Decisão</option><option value="constraint">Restrição</option><option value="fact">Fato</option><option value="artifact">Artefato</option><option value="goal">Objetivo</option></select></label>
    <label htmlFor="knowledge-search-order">Ordenação<select id="knowledge-search-order" value={order} onChange={(event) => setOrder(event.target.value as SessionMemoryOrder)}><option value="newest">Mais recentes</option><option value="oldest">Mais antigas</option></select></label>
    <Button type="submit">Buscar</Button>
  </form>;
}

function ProjectList({ projects, selected, choose }: { projects: readonly ProjectDto[]; selected: ProjectDto | null; choose(project: ProjectDto): void }) {
  return <Card title="Projetos" eyebrow="Memória disponível"><ul className="knowledge-selection-list">{projects.map((project) => <li key={project.project_id}><button type="button" aria-pressed={selected?.project_id === project.project_id} onClick={() => choose(project)}><strong>{project.name}</strong><span>{project.project_id}</span></button></li>)}</ul></Card>;
}

function MemoryList({ items }: { items: readonly SessionMemoryDto[] }) {
  return <ul className="knowledge-memory-list">{items.map((entry) => <li key={entry.memory_id}><header><strong>{formatMemoryKind(entry.kind)}</strong><time dateTime={entry.created_at}>{formatDate(entry.created_at)}</time></header><p>{entry.content}</p><small>{entry.source_execution_id ? `Execução ${entry.source_execution_id}` : "Origem manual"}</small></li>)}</ul>;
}

function appendUnique(current: readonly SessionMemoryDto[], incoming: readonly SessionMemoryDto[]): readonly SessionMemoryDto[] {
  const identifiers = new Set(current.map((item) => item.memory_id));
  return [...current, ...incoming.filter((item) => !identifiers.has(item.memory_id))];
}

function Loading({ label }: { label: string }) { return <p role="status">{label}...</p>; }

function ErrorState({ title, message, retry, retryLabel = "Tentar novamente" }: { title: string; message: string; retry(): void; retryLabel?: string }) {
  return <div role="alert" className="knowledge-inline-state"><strong>{title}</strong><p>{message}</p><Button type="button" onClick={retry}>{retryLabel}</Button></div>;
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="knowledge-inline-state"><strong>{title}</strong><p>{message}</p></div>;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
