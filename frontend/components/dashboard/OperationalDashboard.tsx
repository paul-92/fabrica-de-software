"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createDashboardLoader,
  type DashboardData,
  type DashboardLoader,
} from "../../lib/services/dashboard";
import { PageHeader } from "../layout/PageHeader";
import { DashboardError } from "./DashboardError";
import { DashboardMetrics } from "./DashboardMetrics";
import { DashboardSkeleton } from "./DashboardSkeleton";
import { EmptyState } from "./EmptyState";
import { RecentRuns } from "./RecentRuns";

type DashboardState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: DashboardData };

export function OperationalDashboard({ loader }: { loader?: DashboardLoader }) {
  const effectiveLoader = useMemo(
    () => loader ?? createDashboardLoader(),
    [loader],
  );
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<DashboardState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    effectiveLoader.load().then(
      (data) => current && setState({ status: "ready", data }),
      () => current && setState({ status: "error" }),
    );
    return () => {
      current = false;
    };
  }, [effectiveLoader, attempt]);

  function retry() {
    setState({ status: "loading" });
    setAttempt((current) => current + 1);
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operações"
        title="Visão geral"
        description="Acompanhe a saúde das execuções e a atividade recente da plataforma."
      />
      {state.status === "loading" ? <DashboardSkeleton /> : null}
      {state.status === "error" ? <DashboardError retry={retry} /> : null}
      {state.status === "ready" ? (
        <>
          <DashboardMetrics metrics={state.data.metrics} />
          {state.data.recentRuns.length === 0 ? (
            <EmptyState />
          ) : (
            <RecentRuns runs={state.data.recentRuns} />
          )}
        </>
      ) : null}
    </div>
  );
}
