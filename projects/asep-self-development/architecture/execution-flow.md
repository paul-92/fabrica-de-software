# Execution Flow

**ID:** ARCH-FLW-001 | **Versão:** 0.1.0 | **Status:** approved

## Fluxo ponta a ponta

1. `asep project init/open`: Project Loader valida raiz e manifesto.
2. `asep validate`: loaders fazem parse seguro; Pydantic valida schemas; referências
   e grafo são verificados sem efeitos.
3. `asep workflow start`: Orchestrator fixa versões, cria `workflow_run` e etapas
   `pending`; State Manager grava snapshot atômico e auditoria.
4. `asep run next`: Workflow Engine seleciona somente a primeira etapa `ready`.
5. Input Validator confere required inputs do contrato.
6. Runtime executa o adaptador atribuído; na 0.1, o BA Adapter renderiza Markdown
   apenas com dados fornecidos.
7. Artifact Manager grava arquivo e manifesto; outputs são revalidados.
8. Gate Evaluator vincula evidências. Se depender de humano, cria Approval Request
   e muda etapa/projeto para `awaiting_approval`.
9. `asep approve|reject`: Approval Manager registra autoridade declarada e decisão.
10. `asep resume`: revalida versões, inputs e dependências antes da nova tentativa.
11. `asep cancel`: confirma, encerra projeto/workflow/etapas não terminais e preserva histórico.
12. `asep status`: consulta snapshots e auditoria sem mutação.

## Ordem transacional

Validar → preparar novo snapshot → escrever artefatos temporários → substituir
artefatos/snapshot → anexar evento de auditoria → apresentar resultado. Se a
auditoria falhar depois do snapshot, registrar recovery marker na próxima abertura;
o desenho detalhado será testado como cenário de crash.

## Determinismo

Mesmas entradas, versões, template e clock/ID controlados produzem a mesma
estrutura de saída. Timestamps e IDs são injetados para teste. Não há execução
paralela nem chamada externa.
