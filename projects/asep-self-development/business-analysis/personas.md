# Personas provisórias

**ID:** BA-PER-001 | **Versão:** 0.1.0 | **Status:** hipóteses  
**Dono:** Business Analyst | **Data:** 2026-07-28

Não há pesquisa com usuários. Os perfis abaixo são **proto-personas**, úteis apenas
para levantar perguntas e cenários; não são fatos confirmados.

## P-01 — Operador de projeto ASEP

**Hipótese:** pessoa responsável por iniciar, inspecionar, bloquear, retomar e
cancelar uma execução local.

- objetivo: aplicar o workflow sem depender de memória tácita;
- necessidades propostas: comandos previsíveis, mensagens acionáveis, confirmação
  antes de ações materiais e visualização clara do estado;
- risco se a hipótese for falsa: a CLI e os fluxos podem atender ao público errado;
- validação: entrevista e teste de tarefa com operador nomeado.

## P-02 — Responsável por aprovação

**Hipótese:** Sponsor, Product, Quality ou Security recebe solicitações estruturadas
e registra decisão.

- objetivo: entender contexto, alternativas, impacto e evidência antes de decidir;
- necessidades propostas: identificar autoridade, condições e histórico;
- validação: walkthrough do fluxo de aprovação com responsáveis nomeados.

## P-03 — Mantenedor da ASEP

**Hipótese:** pessoa que altera Registry, contratos e workflows e precisa detectar
incompatibilidades antes da execução.

- objetivo: evoluir componentes sem quebrar projetos;
- necessidades propostas: validação, erros localizáveis e versões fixadas;
- validação: exercício de mudança declarativa durante o piloto.

## Pergunta bloqueante

Quem representa cada perfil e quais tarefas reais devem ser usadas na validação?
