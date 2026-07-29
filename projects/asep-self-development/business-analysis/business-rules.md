# Regras de Negócio

**ID:** BA-BR-001 | **Versão:** 0.1.0 | **Status:** proposta derivada do Core  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Regra | Fonte | Exceção/decisão |
|---|---|---|---|
| BR-001 | projeto e execução usam IDs e versões identificáveis | SYSTEM/Registry | mudança segue governança |
| BR-002 | etapa só inicia com dependências e entradas obrigatórias válidas | SYSTEM/contratos | lacuna crítica bloqueia |
| BR-003 | gate sem evidência não pode ser aprovado | QUALITY | exceção formal com autoridade |
| BR-004 | agente não pode aprovar o próprio conflito de interesse | AGENTS/GOVERNANCE | nenhuma identificada |
| BR-005 | aprovação humana registra autoridade, decisão, data e condições | SYSTEM | nenhuma identificada |
| BR-006 | falha nunca avança silenciosamente o estado | SYSTEM | nenhuma |
| BR-007 | cancelamento preserva histórico e deveres de retenção | workflow | nenhuma |
| BR-008 | retomada revalida contexto, versões, dependências e aprovações | workflow | nenhuma |
| BR-009 | artefato específico pertence ao projeto | SYSTEM | global somente após aprovação |
| BR-010 | Registry cataloga componentes, não estado da execução | SYSTEM | nenhuma |
| BR-011 | decisão material permanece humana | GOVERNANCE | rito emergencial documentado |
| BR-012 | integração externa de IA não é precondição para operar | escopo fornecido | alteração exige decisão |

## Conflitos

Nenhum conflito entre regras foi identificado. O nível de automatização da
aprovação humana permanece uma decisão de design posterior, sem alterar BR-005.
