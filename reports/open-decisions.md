# Decisões Humanas Pendentes

**Data:** 2026-07-28  
**Dono do acompanhamento:** Paulo Cesar, Product Owner, e Executive  
**Status:** aguardando decisões humanas

Esta lista contém somente escolhas que não podem ser tomadas pela implementação.
As aprovações de escopo, stack e Arquitetura 0.1 foram concluídas e, por isso,
não aparecem como pendências.

| Decisão | Contexto | Alternativas | Impacto | Recomendação | Urgência |
|---|---|---|---|---|---|
| Nomear autoridades restantes | Product Owner Paulo Cesar foi nomeado; Quality e Security ainda não | nomear pessoas; autorizar responsáveis interinos com prazo | afeta independência dos gates técnicos e aceite de risco | nomear antes dos respectivos gates | alta |
| Aprovar política de dados para IA | Não há provedor, classificação permitida ou retenção aprovados | somente público/sintético; ambiente privado; fornecedores avaliados | determina privacidade e liberação de integrações futuras | manter integrações externas fora do escopo até avaliação formal | alta |
| Definir ferramenta e meta de cobertura | pytest foi aprovado, mas medição e limiar de cobertura não foram | pytest-cov; ferramenta externa; adiar métrica por linha | afeta gate automatizado e dependências de desenvolvimento | avaliar pytest-cov e aprovar limiar baseado em risco | média |
| Definir destino dos documentos históricos | Agregados de compatibilidade permanecem no repositório | deprecar; incorporar conteúdo; manter por prazo | afeta consumidores e manutenção | inventariar consumidores antes de remover | baixa |

## Condição para próximos avanços

O núcleo local da Sprint 1 está autorizado e concluído. O tailoring sequencial
da Sprint 2 foi registrado no ADR-014. Integração com IA externa continua bloqueada até
aprovação da política de dados. Gates de Quality e Security exigem autoridades
nomeadas ou delegação humana explícita.
