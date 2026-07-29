# ADR-002 — Estrutura do código-fonte

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Typer, PyYAML, Jinja2 e filesystem são detalhes; regras de estado/gates precisam
de testes rápidos.
## Problema
Impedir acoplamento do domínio a frameworks sem criar camadas cerimoniais.
## Alternativas
Organizar por tecnologia; organizar por feature sem direção de dependência;
domain/application/ports/adapters/interfaces.
## Decisão
Separar `domain`, `application`, `ports`, `adapters` e `interfaces/cli`, agrupando
submódulos por capacidade dentro das camadas.
## Justificativa
Dependências apontam para dentro; adaptadores podem ser substituídos em teste.
## Consequências
Mais interfaces explícitas e mapeamento entre modelos de IO/domínio; CLI fica fina.
## Riscos
Boilerplate. Criar porta somente para filesystem, clock/IDs, agentes e sinks
realmente substituíveis.
