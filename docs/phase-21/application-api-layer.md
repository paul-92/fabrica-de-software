# Fase 21 — Application/API Layer

**Público:** engenharia, arquitetura e consumidores de interfaces externas  
**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** concluída

## Objetivo

Fornecer uma fronteira estável de aplicação para Intelligent Engineering e
um adapter HTTP que a exponha sem acoplar apresentação ou transporte ao Core.

## Arquitetura final

```text
HTTP Client
    ↓
FastAPI / HTTP DTOs
    ↓
Application Layer
    ↓
Intelligence
    ↓
Planning + Autonomous Engineering
```

HTTP conhece a Application Layer. A Application Layer delega a uma capability
de Intelligence. Intelligence compõe Planning e Autonomous Engineering sem
fundir os dois domínios.

## 21.1 — Application Contracts & Intelligent Facade

A fronteira pública é formada por:

- `IntelligentEngineeringCapability`, porta mínima para a capacidade interna;
- `ApplicationIntelligentEngineeringRequest`, entrada estrita e imutável;
- `ApplicationIntelligentEngineeringResult`, saída estrita e imutável;
- `IntelligentEngineeringApplicationService`, fachada que delega uma vez e
  preserva os resultados internos.

A fachada não constrói infraestrutura, não reimplementa Planning, Repair,
Learning ou Intelligence e propaga erros para a política do adapter chamador.

## 21.2 — Application Composition

`create_intelligent_engineering_application_service(planner, engineering)` é
o composition root específico do caso de uso. Ele constrói internamente:

- `KnowledgeAwarePlanningAdapter`;
- `IntelligentEngineeringService`;
- `IntelligentEngineeringApplicationService`.

`Planner` e `AutonomousEngineeringExecutor` permanecem dependências
explícitas. Não existe container global, service locator, singleton oculto ou
criação arbitrária de storage.

## 21.3 — HTTP/API Adapter for Intelligent Engineering

O endpoint público é:

```text
POST /api/v1/intelligent-engineering/execute
```

O adapter define DTOs HTTP próprios e estritos para Planning, conhecimento,
memória, análise de falha, reparo e reflexão. Mapeadores determinísticos fazem:

```text
HTTP request DTO -> ApplicationIntelligentEngineeringRequest
ApplicationIntelligentEngineeringResult -> HTTP response DTO
```

O `IntelligentEngineeringApplicationService` é injetado explicitamente em
`create_app`. Quando ele não é configurado, o router não é registrado. O
adapter HTTP não instancia PlanningEngine, Autonomous Engineering, Memory,
Learning, repositories ou SQLite.

Entradas HTTP claramente inválidas, incluindo categoria/importância de memória
e identificadores obrigatórios, são rejeitadas com `422` antes do mapping para
o domínio. Erros inesperados usam a política HTTP segura existente e não
expõem stack trace.

## 21.4 — End-to-End API Integration

O teste E2E comprova o fluxo:

```text
HTTP -> DTO/mapping -> Application -> Intelligence
     -> PlanningEngine + AutonomousEngineeringService
     -> Application Result -> HTTP mapping -> JSON response
```

O cenário confirma conhecimento aprendido chegando a
`PlanningContext.memory`, deduplicação por `memory_id`, execução única de
Planning e Autonomous Engineering, resposta contendo planejamento, proposta,
plano de reparo, resultado, reflexão e estatísticas, e ausência de retry
automático quando `should_retry=True`.

No teste, Proposal Planner e Repair Executor são fakes controlados somente nas
fronteiras que impedem um E2E seguro: não existe Proposal Planner concreto
apropriado e o Repair Executor real envolveria efeitos por Tools,
subprocess/filesystem. Esses fakes são infraestrutura de teste, não
implementações de produção.

## Fronteiras preservadas

- FastAPI e DTOs permanecem em `asep.api`;
- `asep.application` não importa FastAPI nem schemas HTTP;
- HTTP depende da fachada de Application, não de implementações do Core;
- nenhuma infraestrutura concreta é criada pelo adapter HTTP;
- nenhuma recommended action é executada automaticamente;
- `should_retry` continua recomendação, não comando;
- não há IA externa, retry novo ou framework de DI.

## Evidência e limitação ambiental

`tests/qa/application` cobre contratos, fachada e composition root.
`tests/qa/api` cobre validação HTTP, mappings, erros, compatibilidade, OpenAPI e
o E2E completo.

A suíte completa pode apresentar uma falha ambiental conhecida no teste
legado Windows de multiprocessing: `PermissionError` (`WinError 5`) ao criar
named pipe. A falha ocorre antes do comportamento sob teste e não representa
regressão da Fase 21.

## Próxima fase

A Fase 22 — White-label Presentation Layer / Graphical Interface construirá a
interface visual consumindo exclusivamente as fronteiras públicas de
Application/API, sem acoplamento direto ao Core.

Requisitos já definidos para a futura GUI:

- white-label;
- nome do produto, logo, identidade visual, tema e cores configuráveis;
- nenhuma identidade específica de cliente no Core;
- visões de Dashboard, Projetos, Execuções, Agentes e Planning;
- visões de Knowledge/Memory, timeline/logs e métricas/quality gates;
- configurações da apresentação e da aplicação.

## Decisões

Nenhum ADR novo foi necessário. A fase aplica as fronteiras existentes entre
transporte, Application, Intelligence e Core; não introduz decisão transversal
nova.
