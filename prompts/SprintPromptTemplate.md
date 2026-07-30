# Modelo de prompt de Sprint

## Contexto

Descreva estado comprovado, branch, componentes existentes e decisões vigentes.

## Objetivo

Declare um resultado único e verificável.

## Escopo

- componentes a criar ou alterar;
- contratos e integrações;
- comportamento esperado.

## Fora de escopo

- funcionalidades futuras;
- mudanças incompatíveis;
- refatorações não necessárias.

## Arquitetura

Defina responsabilidades, dependências permitidas, invariantes e isolamento.

## Integração

Descreva pontos de entrada, fluxo, persistência, erros e compatibilidade.

## Testes

Liste cenários unitários, integração, regressão e plataformas relevantes.

## Documentação

Liste documentos canônicos a atualizar conforme
[DocumentationStandard.md](DocumentationStandard.md).

## Critérios de aceite

Use itens objetivos, observáveis e vinculados a testes ou inspeção.

## Comandos obrigatórios

```text
python -m pytest -v
python -m compileall src tests
git diff --check
```

## Relatório final

Informar contexto, arquivos, arquitetura, testes, evidências, decisões, riscos,
pendências e `git diff --stat`.

Não fazer commit nem push automaticamente.

