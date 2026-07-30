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

[Fase 07](Phase-07.md), [Sprint 7.5](../phase-07/Sprint-7.5-SQLite-Repository.md)
e [ADR-016](../adr/ADR-016-sqlite-persistence.md).

## Relacionado a

Fase 07; Sprint 7.5; Architecture v1; Roadmap; ADR-016; glossário; testes de
persistência.
