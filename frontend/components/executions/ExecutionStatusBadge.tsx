import { RunStatusBadge } from "../dashboard/RunStatusBadge";

export function ExecutionStatusBadge({ status }: { status: string }) {
  return <RunStatusBadge status={status} />;
}
