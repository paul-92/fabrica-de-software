export function formatTimestamp(value: string | null): string {
  if (value === null) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatDuration(startedAt: string, finishedAt: string | null): string {
  if (finishedAt === null) return "—";
  const duration = Date.parse(finishedAt) - Date.parse(startedAt);
  if (!Number.isFinite(duration) || duration < 0) return "—";
  const seconds = Math.round(duration / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return remaining === 0 ? `${minutes}m` : `${minutes}m ${remaining}s`;
}
