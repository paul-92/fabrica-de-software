# Sumário Executivo — Primeira versão executável da ASEP

**ID:** BA-ES-001  
**Versão:** 0.1.1  
**Status:** aprovado; `QG-ANALYSIS` aprovado  
**Dono:** Business Analyst  
**Data:** 2026-07-28

## Objetivo

Definir o problema, os resultados, o escopo candidato e os requisitos para a
primeira versão executável da ASEP, sem antecipar arquitetura ou tecnologia.

## Fatos confirmados

- a ASEP já possui Core, Registry, contratos, workflows e quality gates documentais;
- o projeto está classificado como `software` e usa `software-project@0.1.0`;
- a primeira interface solicitada é linha de comando, com execução local;
- integração com provedores externos de IA não é obrigatória;
- não há autorização para código de produção nesta etapa.

## Decisão aprovada

O MVP é um executor local por linha de comando que instancia um projeto,
carrega e valida componentes declarativos, conduz etapas sequenciais, persiste
estado e artefatos, interrompe em gates/aprovações e permite falhar, cancelar e
retomar com trilha auditável.

Paulo Cesar, Product Owner, aprovou em 2026-07-28: escopo `0.1`, objetivo,
Registry, Workflow Engine, Runtime, Orchestrator, Business Analyst, geração de
Markdown, Logging e Quality Gates. Paralelismo,
interface gráfica, serviço remoto, integração obrigatória com IA e execução
autônoma de especialistas ficam fora do MVP candidato.

A stack aprovada é Python 3.12+, Typer, Pydantic, PyYAML, Rich, Jinja2 e pytest.
Esta decisão restringe opções técnicas, mas não define a arquitetura.

## Situação do gate

O conteúdo de produto foi aprovado por Paulo Cesar. O Business Analyst, owner
registrado do `QG-ANALYSIS`, reaplicou o gate e aceitou as evidências após a
decisão humana de escopo. Não foi identificada autoaprovação de decisão material:
o aceite de escopo/MVP pertenceu ao Product Owner.

## Recomendação

Iniciar Architecture com o Software Architect, preservando as perguntas abertas e
sem extrapolar a stack para decisões arquiteturais ainda não tomadas.
