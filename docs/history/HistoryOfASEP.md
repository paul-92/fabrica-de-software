# História arquitetural da ASEP

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** história viva

## Visão Geral

Este documento conta como capacidades arquiteturais foram construídas; não é
um changelog. O capítulo atual registra a evolução até a persistência SQLite.

## O Problema

Conhecimento apenas em commits e código perde contexto: futuras equipes veem o
“como”, mas não o caminho, impacto e aprendizados.

## A Solução

Registrar por fases os problemas que motivaram cada transformação e vincular
fotografias de Sprint, ADRs e documentação técnica.

## Explicação simples

É a biografia da plataforma: por que ela ganhou cada parte e como uma etapa
preparou a próxima.

## Explicação técnica

A história preserva contexto e rastreabilidade, enquanto Architecture v1
descreve o estado atual e ADRs fixam decisões.

## Componentes envolvidos

Toda a plataforma; neste capítulo: Run, Timeline, repositories, Factory,
Configuration, SQLite, Query, Metrics e Dashboard.

## Fluxo completo

```text
memória -> repositories de arquivo -> Factory -> Configuration -> SQLite
   |              |                    |           |             |
modelo       durabilidade         seleção       defaults/env   transação local
```

Cada passo reduziu um risco antes de adicionar o próximo.

## Dependências

Esta narrativa depende das evidências do código, testes, Roadmap e ADRs. Não
cria requisitos.

## Exemplos

### Capítulo — Fase 07: da abstração à persistência SQLite

A ASEP já consultava Runs e Timeline por portas em memória. O primeiro desafio
foi sobreviver ao encerramento do processo; backends JSON trouxeram
durabilidade e exigiram escrita atômica. Em seguida, a criação concreta foi
centralizada na Factory. Configuration eliminou valores espalhados e permitiu
seleção ambiental.

Com essas fronteiras prontas, a Sprint 7.5 adicionou SQLite sem alterar
serviços. O impacto foi durabilidade transacional local, atualização por linha
e índice de Timeline. O aprendizado central foi que a sequência importou:
contratos e composição estáveis tornaram o novo backend incremental.

SQLite não resolveu tudo. Migrations, concorrência avançada, backup e operação
distribuída ficaram explicitamente fora. A plataforma terminou a fase preparada
para avaliar essas necessidades com evidência, não antecipação.

### Capítulo — Fase 08: coordenação antes de inteligência

Com persistência e consulta estáveis, a ASEP iniciou a coordenação genérica de
workflows. A Sprint 8.1 deliberadamente não adicionou agentes inteligentes:
primeiro validou ordem, Context compartilhado, falha, cancelamento e resultado
estruturado com Steps simuladas. Runs e Timeline tornaram o fluxo imediatamente
visível para Metrics e Dashboard. O aprendizado foi preservar o Orchestrator
de projetos existente e criar uma fronteira incremental, documentada no
ADR-017.

Na Sprint 8.2, o loop foi extraído para um Engine composto. Validator, Executor
e StepExecutor reduziram a responsabilidade do Orchestrator, preservando os
contratos públicos da Sprint anterior.

As Sprints 8.3 e 8.4 introduziram, em sequência, o contrato formal de Agent e
um Registry em memória. A integração permaneceu na composição por
`AgentStepAdapter`: o Engine continua sem localizar agentes. Identidade única,
listagem determinística e ausência de Singleton prepararam evolução futura sem
antecipar persistência ou plugins.

Na Sprint 8.5, a plataforma passou a guardar uma fotografia especializada de
cada workflow. A decisão foi persistir dados neutros, não Context ou Steps
executáveis. O Orchestrator ganhou uma porta opcional, enquanto o Engine
permaneceu puro. Factory, configuração e os três backends da Fase 7 foram
reutilizados.

A Sprint 8.6 não ampliou o produto. Auditorias, cobertura e revisão documental
consolidaram o RC1. A declaração técnica permaneceu separada da publicação:
Git, CI, scanner de histórico e clone limpo continuam gates humanos/operacionais.

### Capítulo — Fase 09: uma fronteira antes da autonomia

A Sprint 9.1 iniciou agentes inteligentes sem introduzir autonomia. O contrato
de Agent já existia, mas faltava um único lugar para resolver Registry, validar
capability, aplicar política e observar cada chamada. O novo runtime foi
colocado entre `AgentStepAdapter` e Agent; assim, o Engine permaneceu genérico e
o Registry permaneceu catálogo.

Retry explícito, timeout observacional, resultados estruturados, Timeline,
métricas e idempotência local formaram um lifecycle determinístico. O
aprendizado foi tratar segurança e correlação como parte da fronteira desde o
início, mantendo input/output fora dos eventos. Autonomia, concorrência e
controle distribuído permaneceram deliberadamente fora.

Na Sprint 9.2, capacidades externas ao agente ganharam fronteira própria.
Filesystem, documentação e pytest deixaram de ser dependências implícitas:
contratos, Registry e um serviço de execução passaram a aplicar contenção,
política e observabilidade. A primeira coleção de Tools privilegiou leitura e
diagnóstico; escrita e shell genérico foram excluídos por segurança.

Na Sprint 9.3, a continuidade entre execuções deixou de depender de estado
implícito. MemoryStore separou persistência, MemoryService concentrou retenção e
segurança, e ContextBuilder preparou o input do agente sem acoplar o Runtime ao
SQLite. A solução permaneceu lexical e operacional; busca vetorial foi
preparada por portas substituíveis, não simulada.

Na Sprint 9.4, a intenção passou a ser explicitada antes da ação. Um Planning
Engine determinístico combinou objetivo, contexto, memória, Tools e workflow
em um ExecutionPlan validado. A integração permaneceu opcional e por porta,
preservando o Workflow Engine e o Agent Runtime, enquanto Timeline e métricas
separaram claramente planejamento de execução. Nenhuma autonomia ou LLM foi
introduzida.

Na Sprint 9.5, planos passaram a ser distribuídos entre agentes registrados
sem transformar Planning ou Runtime em coordenadores. Assignment tornou
rastreável a ligação entre etapa, capability e agente; uma fila sequencial
respeitou dependências, e o agregador devolveu resultado consolidado. A
separação preservou contratos para futura fila paralela, sem afirmar
distribuição que ainda não existe.

Na Sprint 9.6, o Runtime ganhou uma camada externa de supervisão. Falhas
passaram a ser classificadas antes de retry ou fallback, e uma máquina de
estados tornou explícita a terminação. O Supervisor preservou a porta do
Runtime, permitindo ao Coordinator adotar resiliência por composição. Rollback
foi representado como estado futuro, não simulado como comportamento existente.

Na Sprint 9.7, as fronteiras da Fase 9 foram conectadas por uma fachada única.
Um objetivo passou pelo Workflow, planejamento, coordenação, supervisão,
Runtime, Tools e memória, retornando um GoalResult observável. O Pipeline não
substituiu nenhum mecanismo: apenas tornou a composição utilizável e preparou
entradas futuras sem implementar CLI, REST, Web ou LLM.

Na Sprint 9.8, a Fase 9 foi congelada para auditoria. A revisão confirmou zero
ciclos internos, executou 794 testes, mediu 95% de cobertura e validou os
exemplos. Inconsistências entre estado, roadmap e índices foram corrigidas sem
alterar comportamento de produção. O RC2 foi declarado tecnicamente validado,
mas publicação, CI multiplataforma, scanner de histórico e revisão humana
permaneceram gates operacionais separados.

### Capítulo — Fases 10–16: da descrição ao software validado

A Fase 10 estruturou necessidades de negócio em modelos, requisitos e
blueprints determinísticos. As Fases 11 e 12 conectaram esse resultado,
respectivamente, ao Planning e à Coordination sem fundir os domínios. As Fases
13 e 14 comprovaram o caminho até o Runtime e do `DeveloperAgent` até Tools
reais.

Na Fase 15, `IntelligentOrchestratorService` reuniu construção do blueprint,
planejamento, coordenação, artefatos e gates numa fachada tipada. Na Fase 16,
efeitos controlados completaram o fluxo: `WriteFileTool` materializa conteúdo
no workspace, `RunTestsTool` executa pytest e falhas percorrem AgentResult e
Quality Gate até o status consolidado. O aprendizado foi reutilizar contratos
existentes e manter efeitos e qualidade fora dos agentes.

## Testes

A história é conferida contra testes de contrato, testes SQLite e imports
arquiteturais. Links locais são validados na revisão documental.

## Erros comuns

Tratar este arquivo como roadmap futuro ou copiar afirmações não implementadas.
O código é a fonte da verdade.

## Limitações

Capítulos anteriores ainda não foram reconstruídos com o mesmo detalhe; isso
não autoriza inventar retrospectivas.

## Evolução futura

Novas fases devem acrescentar capítulos preservando os existentes e apontando
para evidências.

## Referências

[Fase 07](Phase-07.md), [Fase 08](Phase-08.md),
[Sprint 8.4](../phase-08/Sprint-8.4-Agent-Registry.md) e
[ADR-020](../adr/ADR-020-in-memory-agent-registry.md).
Fase 9: [Sprint 9.1](../phase-09/Sprint-9.1-Intelligent-Agent-Runtime.md) e
[ADR-022](../adr/ADR-022-intelligent-agent-runtime.md);
[Sprint 9.2](../phase-09/Sprint-9.2-Tool-Registry.md) e
[ADR-023](../adr/ADR-023-tool-registry.md);
[Sprint 9.3](../phase-09/Sprint-9.3-Agent-Memory.md) e
[ADR-024](../adr/ADR-024-agent-memory.md);
[Sprint 9.4](../phase-09/Sprint-9.4-Planning-Engine.md) e
[ADR-025](../adr/ADR-025-planning-engine.md);
[Sprint 9.5](../phase-09/Sprint-9.5-Multi-Agent-Coordination.md) e
[ADR-026](../adr/ADR-026-multi-agent-coordination.md);
[Sprint 9.6](../phase-09/Sprint-9.6-Execution-Recovery.md) e
[ADR-027](../adr/ADR-027-execution-recovery.md);
[Sprint 9.7](../phase-09/Sprint-9.7-EndToEnd.md) e
[ADR-028](../adr/ADR-028-end-to-end-pipeline.md);
[Sprint 9.8](../phase-09/Sprint-9.8-Platform-Hardening-RC2.md) e
[Release Candidate 2](../releases/ReleaseCandidate2.md).

## Relacionado a

Fases 07–16; Architecture v1; Roadmap; ADRs; glossário; testes.
