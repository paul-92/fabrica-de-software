# Workflow: new-project

**Dono:** orchestrator | **Versão:** 0.1.1 | **Status:** ativo

## Objetivo e quando usar

Instanciar projeto e fixar workflow. Executar quando o lifecycle, uma condição do workflow
declarativo ou uma decisão registrada exigir esta fase.

## Pré-condições e entradas

- projeto e execução identificados;
- contrato do agente, versões e autoridade válidos;
- artefatos predecessores exigidos pelo contrato;
- restrições, riscos e decisões relevantes carregados.

Entrada principal esperada: artefatos predecessores necessários para produzir
`project-record`. Entrada incompatível gera `stage.blocked`, não hipótese silenciosa.

## Procedimento específico

1. Copiar a estrutura-modelo.
2. Atribuir id, tipo, owner e classificação.
3. Fixar workflow e versões dos componentes.
4. Criar estado inicial e evento project.created.
5. Produzir e versionar `project-record`, ligando fontes e decisões.
6. Fazer self-review e obter revisão independente quando o risco exigir.
7. Avaliar `QG-INTAKE` e emitir handoff, eventos e próxima ação.

## Condições, bloqueio e retorno

Etapa pode ser omitida somente quando o workflow permitir e houver justificativa
aprovada. Bloqueio registra causa, impacto, dono e gatilho. Retorno preserva versão
e histórico. Cancelamento preserva auditoria e deveres de retenção.

## Aprovação humana

Obrigatória quando houver mudança material de escopo, custo ou prazo, produção,
acesso sensível, exceção, decisão irreversível ou risco residual alto.

## Saída, gate e conclusão

Saída principal: `project-record` com evidências, riscos, decisões e handoff.
Gate: `QG-INTAKE`. Conclui quando estrutura criada, owners e versão fixados.

## Referências

[`core/LIFECYCLE.md`](../core/LIFECYCLE.md),
[`core/QUALITY.md`](../core/QUALITY.md) e
[`core/COMMUNICATION.md`](../core/COMMUNICATION.md).
