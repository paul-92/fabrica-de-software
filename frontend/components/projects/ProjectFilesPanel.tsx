"use client";

import { useEffect, useMemo, useState } from "react";
import type { WorkspaceEntryDto, WorkspaceFileContentDto } from "../../lib/api/dtos";
import { ApiHttpError } from "../../lib/api/errors";
import { createProjectWorkspaceService, type ProjectWorkspaceService } from "../../lib/services/projectWorkspaceService";
import { Card } from "../Card";

type Props = { projectId: string; service?: ProjectWorkspaceService };

export function ProjectFilesPanel({ projectId, service }: Props) {
  const api = useMemo(() => service ?? createProjectWorkspaceService(), [service]);
  const [children, setChildren] = useState<Record<string, readonly WorkspaceEntryDto[] | null>>({ "": null });
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set([""]));
  const [treeError, setTreeError] = useState<string | null>(null);
  const [file, setFile] = useState<WorkspaceFileContentDto | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.listDirectory(projectId, "").then(
      (directory) => { if (active) { setChildren({ "": directory.entries }); setTreeError(null); } },
      () => { if (active) { setChildren({ "": [] }); setTreeError("Não foi possível carregar os arquivos."); } },
    );
    return () => { active = false; };
  }, [api, projectId]);

  async function toggle(entry: WorkspaceEntryDto) {
    if (expanded.has(entry.path)) { setExpanded((value) => { const next = new Set(value); next.delete(entry.path); return next; }); return; }
    setExpanded((value) => new Set(value).add(entry.path));
    if (children[entry.path] !== undefined) return;
    setChildren((value) => ({ ...value, [entry.path]: null }));
    try { const result = await api.listDirectory(projectId, entry.path); setChildren((value) => ({ ...value, [entry.path]: result.entries })); }
    catch { setChildren((value) => ({ ...value, [entry.path]: [] })); setTreeError("Não foi possível abrir a pasta."); }
  }

  async function open(entry: WorkspaceEntryDto) {
    setFile(null); setFileLoading(true); setFileError(null);
    try { setFile(await api.readFile(projectId, entry.path)); }
    catch (error) {
      const code = error instanceof ApiHttpError ? error.code : "";
      setFileError(code === "WORKSPACE_BINARY_FILE" ? "Arquivos binários não podem ser visualizados." : code === "WORKSPACE_FILE_TOO_LARGE" ? "Este arquivo é muito grande para visualização." : "Não foi possível abrir este arquivo.");
    } finally { setFileLoading(false); }
  }

  return <div className="project-files-layout"><Card title="Arquivos" eyebrow="Pasta do projeto · Somente leitura">
    {children[""] === null ? <p role="status">Carregando arquivos...</p> : treeError ? <p role="alert">{treeError}</p> : children[""].length === 0 ? <p>Pasta vazia</p> : <FileEntries entries={children[""]} childrenByPath={children} expanded={expanded} onToggle={toggle} onOpen={open} />}
  </Card>
  {(fileLoading || fileError || file) ? <Card title="Arquivo" eyebrow="Somente leitura">{fileLoading ? <p role="status">Carregando arquivo...</p> : fileError ? <p role="alert">{fileError}</p> : file ? <><p>{file.path}</p><p>{file.size} bytes · {file.language} · Somente leitura</p><pre><code>{file.content}</code></pre></> : null}</Card> : <div className="file-viewer-empty"><p>Selecione um arquivo para visualizar seu conteúdo.</p></div>}</div>;
}

function FileEntries({ entries, childrenByPath, expanded, onToggle, onOpen }: { entries: readonly WorkspaceEntryDto[]; childrenByPath: Record<string, readonly WorkspaceEntryDto[] | null>; expanded: ReadonlySet<string>; onToggle: (entry: WorkspaceEntryDto) => void; onOpen: (entry: WorkspaceEntryDto) => void }) {
  return <ul className="workspace-tree">{entries.map((entry) => <li key={entry.path}><button type="button" onClick={() => entry.kind === "directory" ? onToggle(entry) : onOpen(entry)}>{entry.kind === "directory" ? (expanded.has(entry.path) ? "▾" : "▸") : "·"} {entry.name}</button>{entry.kind === "directory" && expanded.has(entry.path) ? childrenByPath[entry.path] === null ? <p role="status">Carregando {entry.name}...</p> : childrenByPath[entry.path]?.length === 0 ? <p>Pasta vazia</p> : childrenByPath[entry.path] ? <FileEntries entries={childrenByPath[entry.path]!} childrenByPath={childrenByPath} expanded={expanded} onToggle={onToggle} onOpen={onOpen} /> : null : null}</li>)}</ul>;
}
