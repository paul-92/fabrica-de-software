# Technical Risks

**ID:** ARCH-RSK-001 | **Versão:** 0.1.0 | **Status:** open

| ID | Risco | Impacto | Resposta | Dono/gatilho |
|---|---|---|---|---|
| TR-001 | crash entre snapshot e audit divergir histórico | alto | recovery marker/reconciliação testada | Architect/QA |
| TR-002 | YAML flexível aceitar coerção inesperada | alto | safe_load + modelos estritos | Architect |
| TR-003 | filesystem não garantir replace/lock igual em todos OS | alto | matriz e testes por ambiente | Operations/Product |
| TR-004 | aprovação declarada ser confundida com autenticação | alto | aviso e limite local explícito | Security/Product |
| TR-005 | BA Adapter gerar texto não sustentado | alto | somente dados declarados, StrictUndefined/findings | BA/QA |
| TR-006 | workflow atual conter modo parallel fora do MVP | alto | perfil sequencial explícito ou workflow 0.1 | Product/Architect |
| TR-007 | Jinja2/template permitir acesso indevido | médio | environment restrito e raiz allowlist | Security |
| TR-008 | logs/audit conter dados indevidos | alto | payload allowlist/redaction/teste | Security |
| TR-009 | estado editável manualmente invalidar auditoria | médio | checksum/fingerprint e finding | Architect |
| TR-010 | falta de targets impedir decisão de desempenho | médio | medir piloto e definir baseline | Product/Operations |
| TR-011 | stack aprovada criar dependências desnecessárias | baixo | Rich isolado/opcional; nenhuma dependência extra | Architect |
| TR-012 | escopo modular virar framework abstrato excessivo | médio | portas apenas em fronteiras testáveis | Tech Lead |

## Riscos bloqueantes

Nenhum impede a proposta arquitetural. TR-006 precisa ser resolvido no planejamento
antes de implementar o workflow corporativo atual; a recomendação é criar um
workflow de execução 0.1 sequencial ou tailoring versionado, com aprovação de
Product Owner.
