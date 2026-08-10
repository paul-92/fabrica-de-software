import type { AIRuntimeExecutionMode, SessionMemoryKind } from "./api/dtos";

export function formatExecutionMode(value: AIRuntimeExecutionMode): string {
  return value === "workspace_write" ? "Permitir alterações" : "Somente leitura";
}

export function formatExecutionStatus(value: string): string {
  return ({ succeeded: "Concluído", completed: "Concluído", failed: "Falhou", running: "Executando", pending: "Pendente", cancelled: "Cancelado" } as Record<string, string>)[value] ?? value;
}

export function formatMemoryKind(value: SessionMemoryKind): string {
  return ({ fact: "Fato", constraint: "Restrição", decision: "Decisão", artifact: "Artefato", goal: "Objetivo" } as Record<SessionMemoryKind, string>)[value];
}

export function formatWorkspaceChange(value: string): string {
  return ({ created: "Criado", modified: "Modificado", deleted: "Excluído" } as Record<string, string>)[value] ?? value;
}
