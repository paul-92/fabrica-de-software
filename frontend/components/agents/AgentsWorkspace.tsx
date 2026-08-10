"use client";

import { useEffect, useMemo, useState } from "react";
import type { AgentCatalogItemDto } from "../../lib/api/dtos";
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

export function AgentsWorkspace({ loader }: { loader?: AgentsLoader }) {
  const api = useMemo(() => loader ?? createAgentsLoader(), [loader]);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<AgentsState>({ status: "loading" });

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

  function retry() {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Capacidades"
        title="Agentes"
        description="Consulte o catálogo declarativo de agentes e suas capacidades públicas."
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
        <AgentList items={state.items} />
      ) : null}
    </div>
  );
}

function AgentList({ items }: { items: readonly AgentCatalogItemDto[] }) {
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
        </Card>
      ))}
    </section>
  );
}
