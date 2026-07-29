# Organização e Autoridade

**Dono:** Executive; **status:** ativo

| Decisão | Accountable | Consultados | Aprovação humana |
|---|---|---|---|
| valor, prioridade, aceite | Product Manager | Business, Design, Delivery | Sponsor quando material |
| arquitetura e stack | Tech Lead/Architect | Engineering, Security, Operations | sim se irreversível/alto risco |
| estratégia de qualidade | Quality Lead | Product, Engineering | risco residual material |
| segurança e privacidade | Security | Architect, Legal/Privacy | risco alto |
| release | Product + Operations | Quality, Security | sempre para produção |
| fluxo e bloqueios | Delivery Lead/Orchestrator | donos de estágio | quando muda compromisso |

`roles/` define papéis; `departments/` agrupa competências; `agents/` implementa especialidades. Um agente pode recomendar fora de seu domínio, mas não decidir por ele.
