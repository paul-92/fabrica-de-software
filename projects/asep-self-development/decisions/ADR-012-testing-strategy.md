# ADR-012 — Estratégia de testes

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
O risco concentra-se em estado, validação, recovery e rastreabilidade.
## Problema
Obter confiança sem depender de integração externa.
## Alternativas
Somente E2E; cobertura percentual; pirâmide orientada a risco com pytest.
## Decisão
pytest: unit para domínio; contract para schemas/portas; integration para arquivos;
CLI; E2E do fluxo; recovery/security com fault injection.
## Justificativa
Feedback rápido e evidência diretamente ligada a FR/NFR.
## Consequências
Clock, IDs e ports injetáveis; filesystem temporário; golden Markdown controlado.
## Riscos
Mocks esconderem integração e golden files frágeis. Priorizar fakes/contratos e
normalizar somente campos não determinísticos.
