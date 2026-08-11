"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  AgentCatalogItemDto,
  AgentRuntimeProjectionDto,
} from "../../lib/api/dtos";
import {
  createAgentsLoader,
  type AgentsLoader,
} from "../../lib/services/agents";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";

type AgentsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; items: readonly AgentCatalogItemDto[] };

type RuntimeState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; items: readonly AgentRuntimeProjectionDto[] };

export function AgentsWorkspace({ loader }: { loader?: AgentsLoader }) {
  const api = useMemo(() => loader ?? createAgentsLoader(), [loader]);
  const [attempt, setAttempt] = useState(0);
  const [runtimeAttempt, setRuntimeAttempt] = useState(0);
  const [state, setState] = useState<AgentsState>({ status: "loading" });
  const [runtimeState, setRuntimeState] = useState<RuntimeState>({
    status: "loading",
  });

  useEffect(() => {
    let current = true;
    api.listAgents().then(
      (items) => {
        if (current) setState({ status: "ready", items });
      },
      () => {
        if (current) setState({ status: "error" });
      },
    );
    return () => {
      current = false;
    };
  }, [api, attempt]);

  useEffect(() => {
    let current = true;
    api.listRuntime().then(
      (items) => {
        if (current) setRuntimeState({ status: "ready", items });
      },
      () => {
        if (current) setRuntimeState({ status: "error" });
      },
    );
    return () => {
      current = false;
    };
  }, [api, runtimeAttempt]);

  function retry() {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  function retryRuntime() {
    setRuntimeState({ status: "loading" });
    setRuntimeAttempt((value) => value + 1);
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Capacidades"
        title="Agentes"
        description="Consulte o catálogo declarativo e as métricas operacionais observadas neste processo."
      />
      {state.status === "loading" ? (
        <div className="executions-skeleton" role="status">
          <span className="sr-only">Carregando catálogo de agentes</span>
        </div>
      ) : null}
      {state.status === "error" ? (
        <div className="dashboard-state dashboard-state--error" role="alert">
          <h2>Catálogo de agentes indisponível</h2>
          <p>Não foi possível carregar o catálogo de agentes.</p>
          <Button onClick={retry}>Tentar novamente</Button>
        </div>
      ) : null}
      {state.status === "ready" && state.items.length === 0 ? (
        <div className="dashboard-state">
          <h2>Nenhum agente no catálogo</h2>
          <p>Os agentes aparecerão quando forem declarados publicamente.</p>
        </div>
      ) : null}
      {state.status === "ready" && state.items.length > 0 ? (
        <>
          {runtimeState.status === "error" ? (
            <div className="agent-runtime-error" role="alert">
              <div>
                <h2>Dados operacionais indisponíveis</h2>
                <p>O catálogo continua disponível, mas as métricas operacionais não puderam ser carregadas.</p>
              </div>
              <Button onClick={retryRuntime}>Tentar métricas novamente</Button>
            </div>
          ) : null}
          <AgentList items={state.items} runtimeState={runtimeState} />
        </>
      ) : null}
    </div>
  );
}

function AgentList({
  items,
  runtimeState,
}: {
  items: readonly AgentCatalogItemDto[];
  runtimeState: RuntimeState;
}) {
  const runtimeByAgent = new Map(
    runtimeState.status === "ready"
      ? runtimeState.items.map((item) => [item.agent_id, item] as const)
      : [],
  );

  return (
    <section className="agents-grid" aria-label="Catálogo de agentes">
      {items.map((agent) => (
        <Card key={agent.agent_id} title={agent.name} eyebrow={agent.department}>
          <dl className="agent-details">
            <div><dt>Identificador</dt><dd>{agent.agent_id}</dd></div>
            <div><dt>Versão</dt><dd>{agent.version}</dd></div>
            <div><dt>Status declarativo</dt><dd>{agent.lifecycle_status}</dd></div>
          </dl>
          <div className="agent-capabilities">
            <h3>Capacidades</h3>
            {agent.capabilities.length > 0 ? (
              <ul>
                {agent.capabilities.map((capability) => (
                  <li key={capability}>{capability}</li>
                ))}
              </ul>
            ) : (
              <p>Nenhuma capacidade declarada.</p>
            )}
          </div>
          <AgentOperationalMetrics
            state={runtimeState.status}
            metrics={runtimeByAgent.get(agent.agent_id)}
          />
        </Card>
      ))}
    </section>
  );
}

function AgentOperationalMetrics({
  state,
  metrics,
}: {
  state: RuntimeState["status"];
  metrics?: AgentRuntimeProjectionDto;
}) {
  return (
    <section className="agent-operational" aria-label="Dados operacionais observados">
      <h3>Dados operacionais observados</h3>
      {state === "loading" ? (
        <p role="status">Carregando dados operacionais…</p>
      ) : null}
      {state === "error" ? (
        <p>Dados operacionais indisponíveis para este agente.</p>
      ) : null}
      {state === "ready" && !metrics ? (
        <p>Sem observações operacionais para este agente.</p>
      ) : null}
      {state === "ready" && metrics ? (
        <dl className="agent-runtime-metrics">
          <div><dt>Registrado no runtime</dt><dd>{metrics.registered ? "Sim" : "Não"}</dd></div>
          <div><dt>Execuções</dt><dd>{metrics.execution_count}</dd></div>
          <div><dt>Concluídas</dt><dd>{metrics.succeeded}</dd></div>
          <div><dt>Falhas</dt><dd>{metrics.failed}</dd></div>
          <div><dt>Rejeitadas</dt><dd>{metrics.rejected}</dd></div>
          <div><dt>Canceladas</dt><dd>{metrics.cancelled}</dd></div>
          <div><dt>Tempo esgotado</dt><dd>{metrics.timed_out}</dd></div>
          <div><dt>Novas tentativas</dt><dd>{metrics.retries}</dd></div>
        </dl>
      ) : null}
    </section>
  );
}
