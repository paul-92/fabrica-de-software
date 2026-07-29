# Workflow: code-review

**Dono:** reviewer-independent | **Versão:** 0.1.1 | **Status:** ativo

## Objetivo e quando usar

Realizar revisão independente da mudança. Executar quando o lifecycle, uma condição do workflow
declarativo ou uma decisão registrada exigir esta fase.

## Pré-condições e entradas

- projeto e execução identificados;
- contrato do agente, versões e autoridade válidos;
- artefatos predecessores exigidos pelo contrato;
- restrições, riscos e decisões relevantes carregados.

Entrada principal esperada: artefatos predecessores necessários para produzir
`review-record`. Entrada incompatível gera `stage.blocked`, não hipótese silenciosa.

## Procedimento específico

1. Confirmar escopo e independência do revisor.
2. Inspecionar correção, segurança e compatibilidade.
3. Verificar testes, operação e documentação.
4. Classificar e encerrar achados.
5. Produzir e versionar `review-record`, ligando fontes e decisões.
6. Fazer self-review e obter revisão independente quando o risco exigir.
7. Avaliar `QG-IMPLEMENT` e emitir handoff, eventos e próxima ação.

## Condições, bloqueio e retorno

Etapa pode ser omitida somente quando o workflow permitir e houver justificativa
aprovada. Bloqueio registra causa, impacto, dono e gatilho. Retorno preserva versão
e histórico. Cancelamento preserva auditoria e deveres de retenção.

## Aprovação humana

Obrigatória quando houver mudança material de escopo, custo ou prazo, produção,
acesso sensível, exceção, decisão irreversível ou risco residual alto.

## Saída, gate e conclusão

Saída principal: `review-record` com evidências, riscos, decisões e handoff.
Gate: `QG-IMPLEMENT`. Conclui quando achados resolvidos ou aceitos por autoridade.

## Referências

[`core/LIFECYCLE.md`](../core/LIFECYCLE.md),
[`core/QUALITY.md`](../core/QUALITY.md) e
[`core/COMMUNICATION.md`](../core/COMMUNICATION.md).
