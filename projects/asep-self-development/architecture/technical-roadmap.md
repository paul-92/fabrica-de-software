# Technical Roadmap

**ID:** ARCH-RDM-001 | **Versão:** 0.1.0 | **Status:** approved

## Incrementos recomendados

| Marco | Resultado verificável | Dependências |
|---|---|---|
| T0 | schemas Pydantic e validadores de Registry/contratos/workflows | ADR-004/005 |
| T1 | domínio de estado, eventos, erros e repositories em memória | ADR-006/007/010 |
| T2 | persistência local atômica e audit trail | T1, testes de recovery |
| T3 | Workflow Engine sequencial e Orchestrator | T0–T2 |
| T4 | Artifact Manager/Jinja2 e BA Adapter determinístico | T0/T2 |
| T5 | CLI Typer/Rich com status, approval, resume/cancel | T3/T4 |
| T6 | cenário E2E e hardening de segurança | todos |

Cada marco passa testes antes do seguinte. T0 deve resolver TR-006 e alinhar o
workflow executável 0.1.

## Backlog fora do MVP

- execução paralela e scheduler;
- Web/API/dashboard;
- banco, multiusuário e autenticação;
- plugins e provider de IA real;
- telemetria remota;
- migração automática de schemas;
- edição visual e marketplace;
- assinatura criptográfica de auditoria.

## Gate de entrada em planejamento

Product Owner aceita ADRs/arquitetura; Project Manager nomeia responsáveis,
dependências e critérios dos marcos; Quality/Security são envolvidos antes dos
gates correspondentes.
