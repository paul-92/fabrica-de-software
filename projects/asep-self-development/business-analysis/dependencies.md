# Dependências

**ID:** BA-DEP-001 | **Versão:** 0.1.1 | **Status:** aberto  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Dependência | Dono | Necessária para | Estado/gatilho |
|---|---|---|---|---|
| DEP-001 | Product Owner e autoridade de Escopo | Paulo Cesar | aprovação do escopo/MVP | resolvida |
| DEP-002 | nomeação de Quality Lead | Executive | gates de implementação/teste e estratégia de qualidade | aberta; não bloqueia QG-ANALYSIS |
| DEP-003 | política de dados para IA | Security/Product | qualquer cenário com IA externa | bloqueada; não necessária ao fluxo sem IA |
| DEP-004 | aprovação do primeiro incremento | Product Owner | avançar para gate | resolvida |
| DEP-005 | schemas de artefatos/componentes | Tech Lead futuro | validação implementável | posterior ao gate |
| DEP-006 | cenário e representantes do piloto | Product | validar personas e usabilidade | aberto |
| DEP-007 | ambientes locais suportados | Product/Operations | critérios de portabilidade | aberto |
| DEP-008 | metas de capacidade/desempenho | Product/Operations | NFR-008 | aberto |

## Caminho crítico atual

QG-ANALYSIS foi aprovado após DEP-001 e DEP-004. Architecture está liberada.
DEP-002 permanece necessária antes dos gates de implementação e teste.
