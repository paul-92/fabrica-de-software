# Perguntas Abertas

**ID:** BA-OQ-001 | **Versão:** 0.1.1 | **Status:** aberto  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Pergunta/decisão | Responsável | Impacto | Urgência |
|---|---|---|---|---|
| D-003 | Quais dados e provedores, se algum, podem ser usados em testes de IA? | Security/Product | bloqueia integração externa, não o núcleo sem IA | alta |
| D-005 | Quem atuará como Software Architect? | Product Owner/Executive | necessário após gate | alta |
| D-006 | Quem atuará como Security? | Executive | necessário antes de decisões de proteção | alta |
| D-007 | Quem exercerá Quality Lead nas fases de Implementation e Testing? | Executive | bloqueia gates posteriores, não Architecture | média |
| Q-001 | Quem representa operador, aprovador e mantenedor no piloto? | Product | bloqueia validação de personas/CLI | alta |
| Q-002 | Quais ambientes locais precisam ser suportados? | Product/Operations | afeta portabilidade e aceite | média |
| Q-003 | Qual volume de projetos/etapas e metas de tempo deve orientar o piloto? | Product/Operations | afeta NFR-008 | média |
| Q-004 | Qual política de retenção é exigida para logs, decisões e artefatos? | Governance/Security | afeta auditoria e privacidade | alta |
| Q-005 | O primeiro piloto pode usar apenas dados públicos/sintéticos? | Product/Security | reduz risco | alta |
| Q-006 | Quais documentos históricos ainda possuem consumidores? | Documentation/Product | afeta depreciação | baixa |

## Perguntas técnicas reservadas para fase posterior

Schemas, persistência, concorrência, identidade e tecnologia do Runtime devem ser
analisados pelo Software Architect somente depois do `QG-ANALYSIS`.
