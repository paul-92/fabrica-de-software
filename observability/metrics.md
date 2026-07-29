# Métricas

**Dono:** Product + Operations | **Status:** especificação | **Versão:** 0.1.1

| Métrica | Definição | Uso |
|---|---|---|
| lead time | `completed_at - started_at`, por versão/tipo | previsibilidade |
| tempo bloqueado | soma dos intervalos em `blocked` | impedimentos |
| retorno por gate | retornos / avaliações | qualidade da entrada |
| handoff rejeitado | devoluções por incompatibilidade | qualidade contratual |
| decisão pendente | solicitações abertas por idade | governança |
| falha por estágio | `failed` por causa normalizada | confiabilidade |

Cada métrica registra fórmula, eventos-fonte, janela, dimensões permitidas, dono,
baseline, finalidade e limitações. Não medir produtividade individual por volume.
Validar completude, duplicidade, relógio, cardinalidade e mudanças de schema.
