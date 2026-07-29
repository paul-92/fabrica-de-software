# ADR-005 — Formato e validação do Registry

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Registry é o mecanismo de descoberta e usa múltiplos YAML.
## Problema
Resolver componentes sem aceitar IDs ambíguos ou caminhos inseguros.
## Alternativas
Busca por convenção; arquivo único; catálogos YAML tipados.
## Decisão
Manter catálogos YAML separados por tipo, modelos Pydantic estritos, IDs únicos,
paths relativos sob raiz e validação cruzada/fingerprint antes da execução.
## Justificativa
Alinha a base atual e permite mensagens precisas sem banco.
## Consequências
Mudança de arquivo exige revalidação; Registry permanece imutável na execução.
## Riscos
Custo de validação e divergência manual. Tamanho esperado é pequeno; validator
torna-se gate e cache é apenas otimização futura.
