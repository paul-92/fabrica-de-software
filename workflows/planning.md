# Workflow: planning

**Dono:** project-manager | **Versão:** 0.1.1 | **Status:** ativo

## Objetivo e quando usar

Planejar incrementos, capacidade e dependências. Executar quando o lifecycle, uma condição do workflow
declarativo ou uma decisão registrada exigir esta fase.

## Pré-condições e entradas

- projeto e execução identificados;
- contrato do agente, versões e autoridade válidos;
- artefatos predecessores exigidos pelo contrato;
- restrições, riscos e decisões relevantes carregados.

Entrada principal esperada: artefatos predecessores necessários para produzir
`delivery-plan`. Entrada incompatível gera `stage.blocked`, não hipótese silenciosa.

## Procedimento específico

1. Fatiar resultados em incrementos.
2. Estimar por faixas e explicitar premissas.
3. Mapear capacidade, dependências e caminho crítico.
4. Definir gatilhos de replanejamento.
5. Produzir e versionar `delivery-plan`, ligando fontes e decisões.
6. Fazer self-review e obter revisão independente quando o risco exigir.
7. Avaliar `QG-PLAN` e emitir handoff, eventos e próxima ação.

## Condições, bloqueio e retorno

Etapa pode ser omitida somente quando o workflow permitir e houver justificativa
aprovada. Bloqueio registra causa, impacto, dono e gatilho. Retorno preserva versão
e histórico. Cancelamento preserva auditoria e deveres de retenção.

## Aprovação humana

Obrigatória quando houver mudança material de escopo, custo ou prazo, produção,
acesso sensível, exceção, decisão irreversível ou risco residual alto.

## Saída, gate e conclusão

Saída principal: `delivery-plan` com evidências, riscos, decisões e handoff.
Gate: `QG-PLAN`. Conclui quando backlog executável e riscos com dono.

## Referências

[`core/LIFECYCLE.md`](../core/LIFECYCLE.md),
[`core/QUALITY.md`](../core/QUALITY.md) e
[`core/COMMUNICATION.md`](../core/COMMUNICATION.md).
