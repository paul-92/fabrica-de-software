# Agent Registry

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Porta e implementação em memória para cadastro e consulta de agentes.

## Responsabilidades

O Registry armazena referências, valida contratos, impede IDs duplicados,
consulta metadados, lista e filtra por capacidade. Ele não cria nem executa
agentes.

## Contrato

```python
class AgentRegistry(Protocol):
    def register(self, agent: Agent) -> None: ...
    def unregister(self, agent_id: AgentId) -> None: ...
    def get(self, agent_id: AgentId) -> Agent: ...
    def contains(self, agent_id: AgentId) -> bool: ...
    def list_all(self) -> tuple[Agent, ...]: ...
    def get_metadata(self, agent_id: AgentId) -> AgentMetadata: ...
    def find_by_capability(
        self,
        capability: AgentCapability,
    ) -> tuple[Agent, ...]: ...
```

## Políticas

- identidade: apenas `AgentId`, sem chave composta por versão;
- duplicidade: erro, preservando o original;
- ausência obrigatória: exceção, nunca `None`;
- remoção ausente: exceção;
- listagem: ordem lexicográfica por `AgentId`;
- capacidade: igualdade exata e case-sensitive pelo ID;
- coleções: tuplas, nunca o dicionário interno;
- lifecycle: controlado pela composição, sem singleton.

## Erros

- `AgentRegistryException`;
- `AgentAlreadyRegisteredException`;
- `AgentNotFoundException`;
- `InvalidAgentRegistrationException`.

As exceções carregam `AgentId` quando aplicável e não incluem metadados ou
conteúdo potencialmente sensível.

## Integração com workflow

```text
Composition -> Registry.get(AgentId)
            -> AgentStepAdapter(agent=...)
            -> WorkflowDefinition
            -> WorkflowEngine
```

O Engine não recebe nem importa o Registry. Steps comuns continuam aceitas.

## Segurança e performance

Não há import dinâmico, execução por nome, credenciais, rede ou reflexão. Um
dicionário encapsulado é suficiente para o volume atual. Thread safety não foi
adicionada porque não existe uso concorrente comprovado.

## Limitações

Sem persistência, factory, plugins, discovery, resolução singular, ranking,
health check ou administração por API.

## Referências

[Sprint 8.4](../phase-08/Sprint-8.4-Agent-Registry.md) e
[ADR-020](../adr/ADR-020-in-memory-agent-registry.md).

