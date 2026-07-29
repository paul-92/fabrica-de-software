# ADR-001 — Estilo arquitetural

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
CLI local, fluxo sequencial, equipe/capacidade ainda desconhecidas e necessidade de
provar interfaces sem infraestrutura distribuída.
## Problema
Escolher uma estrutura simples que preserve módulos e testabilidade.
## Alternativas
Script monolítico; modular monolith; microservices/processos distribuídos.
## Decisão
Modular monolith em um processo, com módulos e portas explícitas.
## Justificativa
Evita custo operacional/distribuído, mas impede que CLI e filesystem dominem o
núcleo. É compatível com o MVP e permite extração futura baseada em evidência.
## Consequências
Um pacote/deploy e transações locais simples; disciplina modular depende de testes
e imports. Microservices, filas e containers ficam fora.
## Riscos
Monólito virar acoplamento ou abstração excessiva. Mitigar com ownership, testes e
portas apenas nas fronteiras reais.
