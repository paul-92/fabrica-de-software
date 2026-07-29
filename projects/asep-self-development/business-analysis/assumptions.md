# Hipóteses e Premissas

**ID:** BA-ASM-001 | **Versão:** 0.1.1 | **Status:** hipóteses abertas  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Hipótese | Impacto se falsa | Dono da validação | Gatilho |
|---|---|---|---|---|
| H-001 | uma CLI local atende ao primeiro operador | interface do MVP inadequada | Product Owner | teste com operador |
| H-002 | execução sequencial prova as interfaces principais | piloto não cobre riscos essenciais | Product Owner + Tech | revisão do cenário |
| H-003 | arquivos declarativos atuais são entrada suficiente | schemas precisarão mudar antes do executor | Tech Lead | validação de schema |
| H-004 | aprovação pode começar como pausa e registro local | fluxo humano poderá exigir canal externo | Product/Governance | walkthrough |
| H-005 | um único operador por execução é aceitável no MVP | concorrência poderá ser necessária | Product/Operations | cenário piloto |
| H-006 | dados públicos/sintéticos bastam para o piloto | política de dados bloqueará parte do cenário | Security/Product | aprovação da política |

A escolha de CLI e execução sequencial deixou de ser hipótese de escopo, pois foi
aprovada. Permanece a hipótese de que esse recorte produzirá aprendizado suficiente.
