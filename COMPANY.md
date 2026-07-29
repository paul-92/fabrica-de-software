# Modelo Organizacional da ASEP

**Dono:** Executive  
**Status:** ativo  
**Versão:** 0.1.0

## Propósito

Operar desenvolvimento de software assistido por IA com responsabilidade humana, especialização, rastreabilidade e qualidade verificável.

## Serviços e tipos de projeto

A ASEP suporta discovery, web, mobile, SaaS, APIs, integrações, automações, soluções com IA, modernização e manutenção. O enquadramento detalhado permanece em [docs/service-catalog.md](docs/service-catalog.md); nenhuma categoria impõe uma stack.

## Modelo operacional

O Orchestrator coordena fluxo e evidência; especialistas mantêm autoridade de domínio; Product Manager decide valor, prioridade e aceite; Tech Lead arbitra decisões técnicas; Quality Lead avalia evidência e risco residual; Security pode bloquear risco inaceitável; Sponsor decide orçamento, contrato e impacto material.

## Organização

Papéis estão definidos em `roles/`, áreas em `departments/`, agentes em `agents/` e interfaces em `contracts/`. A matriz formal de autoridade está em [core/ORGANIZATION.md](core/ORGANIZATION.md).

## Portfólio e capacidade

- uma prioridade crítica por equipe;
- capacidade explícita para qualidade, dívida e manutenção;
- throughput, lead time, estabilidade e resultado, nunca linhas de código;
- iniciativas sem hipótese, sponsor ou decisão disponível são reformuladas ou suspensas.

## Cadência e métricas

Planejamento de portfólio mensal, planejamento de entrega semanal, sincronização operacional conforme necessidade, review por marco, revisão operacional mensal e retrospectiva por ciclo. Toda métrica tem definição, fonte, baseline, alvo, frequência e dono.
