# ADR-001 — Limites do núcleo da ASEP

- Status: Proposto
- Data: 2026-07-29
- Responsáveis: Equipe de Engenharia ASEP
- Decisão relacionada: Sprint 3 — Core Architecture

## Contexto

A ASEP já possui uma implementação funcional composta por modelos,
orquestração, execução de workflows, runtime de agentes, registry,
persistência de estado, quality gates, gerenciamento de artefatos e CLI.

Os principais componentes de código estão organizados em `src/asep`,
incluindo:

- `models.py`
- `execution/models.py`
- `execution/engine.py`
- `execution/state.py`
- `orchestrator/service.py`
- `registry/loader.py`
- `workflow/loader.py`
- `runtime/agent_runtime.py`
- `quality/engine.py`
- `artifacts/manager.py`

Com o crescimento da plataforma, existe o risco de modelos de domínio,
configurações YAML, execução, persistência e infraestrutura se tornarem
fortemente acoplados.

Também existe o risco de criar novos modelos que dupliquem conceitos já
presentes em `src/asep/models.py` e `src/asep/execution/models.py`.

## Problema

Precisamos estabelecer limites arquiteturais claros para que:

1. os conceitos centrais da ASEP não dependam de CLI, YAML, sistema de
   arquivos ou provedores de IA;
2. o Orchestrator coordene o fluxo sem executar diretamente o trabalho
   dos agentes;
3. o Runtime execute agentes por meio de contratos estáveis;
4. Registry e Workflow Loader convertam configurações externas em
   objetos utilizados pela aplicação;
5. novos componentes sejam adicionados sem duplicar modelos existentes;
6. a arquitetura atual possa evoluir incrementalmente sem reescrita total.

## Decisão

A ASEP adotará uma arquitetura modular com dependências orientadas para
o núcleo.

A direção geral das dependências será:

```text
CLI
 |
 v
Orchestrator / Application Services
 |
 v
Execution Core
 |
 v
Domain Models and Contracts
YAML / Files / LLM / CLI
          |
          v
      Adapters
          |
          v
 Application Services
          |
          v
 Domain Models and Contracts

 
---

# O que esse ADR está dizendo de verdade

Ele não diz “vamos aplicar Clean Architecture porque parece bonito”.

Ele diz:

> “Não vamos criar uma segunda arquitetura ao lado da que já funciona.”

Isso é importante porque a ASEP já tem código para execução, estado, runtime, registry, workflows e testes. A suíte inclui testes de Orchestrator, Runtime, Engine, State Manager, Registry, CLI e execução ponta a ponta. :contentReference[oaicite:2]{index=2}

Nosso objetivo agora é descobrir:

```text
O que é domínio?
O que é serviço de aplicação?
O que é infraestrutura?
O que está no lugar errado?
O que já está correto?