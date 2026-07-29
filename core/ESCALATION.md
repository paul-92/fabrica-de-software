# Escalonamento

**Dono:** Delivery Lead | **Status:** ativo | **Versão:** 0.1.1

## Gatilhos

Interrompa diante de falta de autorização, entrada crítica ausente, contradição
material, conflito de autoridade, risco alto, incidente, decisão irreversível ou
gate sem evidência. Dúvida não crítica pode seguir como hipótese somente quando o
contrato permitir e houver dono e gatilho.

## Registro mínimo

- fato observado e fontes;
- tarefa/estágio afetado e impacto;
- ações seguras já realizadas;
- alternativas, custos e riscos;
- recomendação sem apresentá-la como decisão;
- autoridade necessária, urgência e prazo;
- condição objetiva de retomada.

## Roteamento

Security/Privacy pode bloquear risco de proteção; Sponsor decide impacto
contratual/orçamentário; Product decide valor, prioridade e aceite; Tech Lead
arbitra arquitetura; Quality decide suficiência da evidência; Executive resolve
conflito entre autoridades.

## Estado e encerramento

A tarefa vai para `blocked` ou `awaiting_approval` e emite o evento correspondente.
A decisão registra quem decidiu, autoridade, condições e data. Antes de retomar,
o agente revalida contexto, versões, dependências e efeitos da espera.
