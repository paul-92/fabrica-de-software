# DEC-STACK-001 — Stack aprovada para a versão 0.1

**Status:** accepted  
**Data:** 2026-07-28  
**Decisor:** Paulo Cesar, Product Owner  
**Escopo:** primeira versão executável da ASEP

## Contexto e decisão

O MVP exige execução local via CLI, leitura e validação de YAML, modelos
declarativos, saída de terminal, geração de Markdown e testes. O Product Owner
aprovou Python 3.12+, Typer, Pydantic, PyYAML, Rich, Jinja2 e pytest.

## Limites

Esta é uma restrição tecnológica de produto. Não define componentes, fronteiras,
persistência ou fluxo interno. Mudança exige change request aprovado.

## Avaliação arquitetural

Necessidade, obrigatoriedade, alternativas e consequências de cada item estão em
[`architecture-decisions.md`](../architecture/architecture-decisions.md). O
Software Architect deve trabalhar dentro da decisão ou solicitar alteração.

## Riscos

A decisão foi fornecida sem comparação formal de alternativas. A Arquitetura
registra impactos e evita adicionar dependências além das aprovadas.

## Histórico do identificador

Este registro foi inicialmente classificado como `ADR-001`. Foi renomeado para
`DEC-STACK-001` antes da fase de Arquitetura porque a sequência ADR-001–ADR-013
foi reservada pelo brief arquitetural. O conteúdo decisório e o decisor foram
preservados; não houve mudança da decisão.
