# ASEP Release Candidate 2

**Público:** engenharia, operação e responsáveis pelo release  
**Dono:** Engenharia ASEP  
**Versão candidata:** 0.1.0-rc2  
**Status:** tecnicamente validado; publicação pendente  
**Data:** 2026-07-30

## Resumo

O RC2 consolida a Fase 9 sobre as bases de Observabilidade, Persistência e
Orquestração do RC1. Ele adiciona ao candidato anterior o Runtime inteligente,
Tool Registry, memória operacional, Planning Engine, coordenação multiagente
sequencial, supervisão/recuperação e o pipeline ponta a ponta exposto por
`asep.execute`.

## Fluxo oficial

```text
Goal
  -> ASEPEngine
  -> Workflow
  -> Planning
  -> Coordinator
  -> Supervisor
  -> Runtime
  -> Tool Registry
  -> Tools
  -> Recovery
  -> Memory
  -> Timeline
  -> Metrics
  -> Persistence
  -> GoalResult
```

Recovery envolve Runtime/Supervisor e Memory/Timeline/Metrics/Persistence são
serviços transversais; a sequência acima é uma visão operacional, não uma
cadeia de imports.

## Funcionalidades consolidadas

- contratos, Registry e execução observável de agentes;
- Tools tipadas, registradas e confinadas ao workspace;
- memória em memória/SQLite, retenção, filtragem e contexto;
- planejamento determinístico e validado;
- atribuição por capability e coordenação sequencial;
- classificação de falha, retry, backoff e fallback;
- execução completa por fachada Python;
- Runs, Timeline e Workflow Snapshots em memory/file/SQLite;
- CLI, Dashboard API e exportadores Mermaid, BPMN e JSON existentes.

## ADRs vigentes

ADRs 016–028 cobrem SQLite, fronteiras do Orchestrator e Workflow Engine,
contratos/Registry de agentes, Workflow Persistence, Runtime inteligente,
Tools, Memory, Planning, Coordination, Recovery e pipeline E2E. O hardening
não mudou decisão arquitetural e, portanto, não criou ADR.

## Estatísticas

| Métrica | Valor |
|---|---:|
| módulos Python em `src/asep` | 179 |
| linhas Python em `src/asep` | 16.373 |
| classes | 433 |
| funções e métodos | 756 |
| Protocols explícitos | 30 |
| ciclos internos de import | 0 |
| testes aprovados | 794 |
| cobertura | 95% |
| módulos de teste | 53 |
| ADRs documentados | 15 |
| documentos Markdown em `docs` | 97 |
| exemplos executáveis revisados | 3 |

## API pública da Fase 9

```python
import asep

result = asep.execute(
    goal="Analise este projeto e explique sua arquitetura.",
    workspace=".",
)
```

O retorno é um `GoalResult` serializável com `run_id`, status, resumo, etapas,
Timeline, métricas, tempo, artefatos e metadados sanitizados.

## Compatibilidade e migração

Nenhuma API existente foi removida. Consumidores podem continuar usando CLI,
API, Orchestrators e serviços diretamente. A fachada é aditiva. Instruções
estão no [Migration Guide RC2](../migration/MigrationGuide-RC2.md).

## Limitações

- pipeline padrão síncrono, sequencial e em memória;
- nenhum LLM ou agente externo é chamado pelo pipeline padrão;
- sem paralelismo, scheduler, REST/Web específicos do pipeline ou retomada
  automática;
- timeout lógico do Runtime não interrompe chamada Python bloqueada;
- Agent/Tool registries e métricas padrão são voláteis;
- MemoryFilter é lexical, não detector universal de segredos;
- sem lockfile, migrations versionadas ou criptografia SQLite;
- validação local feita no Windows; CI multiplataforma está pendente.

## Qualidade e estado

Os 794 testes passaram com 95% de cobertura. `compileall`, `pip check`, três
exemplos e `git diff --check` foram aprovados. Não há bloqueador funcional
conhecido.

O candidato ainda não está publicado: mudanças acumuladas não estão
versionadas e 4.062 arquivos temporários de pytest permanecem no commit base.
Revisão humana, remoção intencional desses temporários, commit/push
autorizados, clone limpo/CI, scanner de histórico e decisão sobre lockfile são
gates operacionais obrigatórios.

## Evidências

[Sprint 9.8](../phase-09/Sprint-9.8-Platform-Hardening-RC2.md),
[Architecture Map](../architecture/ArchitectureMap.md),
[Migration Guide RC2](../migration/MigrationGuide-RC2.md) e
[Documentation Index](../DocumentationIndex.md).
