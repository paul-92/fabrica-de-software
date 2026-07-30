# ADR-029 — Project Analyzer determinístico e isolado

**Status:** aceito  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

A Fase 10 precisa de uma representação estruturada do projeto antes de
introduzir capacidades inteligentes. Integrar essa descoberta diretamente ao
Runtime criaria acoplamento e dificultaria testar heurísticas.

## Decisão

Criar `asep.project_analysis` como módulo independente. `ProjectAnalyzer` é a
fachada; Scanner e detectores possuem responsabilidade única; o Report Builder
monta `ProjectAnalysis` imutável e estrito.

A análise usa somente filesystem local, manifests, extensões, imports e
convenções. Não executa código do projeto, não acessa rede e não depende de
Workflow, agentes, providers, Tools, Memory ou persistência.

## Consequências

O resultado é reproduzível, testável e pode ser consumido futuramente por
outros componentes sem alterar o Analyzer. Heurísticas são evidências, não
certezas, e podem gerar falsos positivos ou negativos. Novos detectores devem
preservar determinismo e registrar evidência.

## Alternativas rejeitadas

- LLM: fora do escopo e não determinístico;
- lógica no Agent Runtime: viola separação;
- ferramenta externa obrigatória: prejudica portabilidade;
- modelo mutável: reduz rastreabilidade.

## Evidência

`src/asep/project_analysis/`, `tests/test_project_analysis.py` e
`docs/project-analysis/`.
