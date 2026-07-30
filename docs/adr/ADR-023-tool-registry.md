# ADR-023 — Tools independentes e mediadas por Registry

**Status:** aceita localmente  
**Data:** 2026-07-30  
**Dono:** Engenharia ASEP

## Contexto

Agentes precisam ler arquivos, consultar documentação e executar testes.
Acesso direto espalharia filesystem e subprocesso por agentes, impediria
políticas uniformes e ampliaria risco de traversal, vazamento e execução
arbitrária.

## Decisão

Criar contratos de Tool, um `ToolRegistry` para localização e um
`ToolExecutionService` para validação, política, execução, Timeline e métricas.

- Tools não conhecem Workflow, Agent Runtime ou providers;
- Registry não executa Tools;
- agentes alcançam Tools pela porta `ToolExecutor`;
- paths passam por uma política comum de workspace;
- `RunTestsTool` monta um comando fixo e usa o ProcessRunner existente;
- API e execução permanecem síncronas;
- implementação inicial do Registry é em memória.

## Alternativas consideradas

1. **Agentes acessam filesystem/subprocess diretamente:** rejeitada por
   segurança, duplicação e baixa auditabilidade.
2. **Registry também executa:** rejeitada por misturar catálogo e caso de uso.
3. **Uma Tool genérica de shell:** rejeitada por permitir execução arbitrária.
4. **Permissões distribuídas e persistência agora:** rejeitadas por ausência de
   requisito comprovado e por ampliar a Sprint.
5. **Acoplar Tools ao Workflow Engine:** rejeitada; o Engine deve continuar
   executando Steps sem conhecer recursos concretos.

## Consequências

Positivas:

- fronteira auditável e testável;
- contenção e filtragem uniformes;
- agentes e Engine independentes de implementações;
- novas Tools podem ser registradas sem alterar consumidores.

Custos e limites:

- Registry, métricas e idempotência são locais;
- não existe autorização granular por agente;
- timeout genérico não é preemptivo;
- cada Tool deve definir seu payload no contrato/documentação.

## Evidência

Código em `src/asep/tools/`, testes `test_tool_registry.py`,
`test_tool_execution.py` e `test_builtin_tools.py`. Visão operacional:
[Tool Architecture](../tools/ToolArchitecture.md).

