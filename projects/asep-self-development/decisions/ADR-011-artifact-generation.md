# ADR-011 — Geração e armazenamento de artefatos

**Status:** accepted | **Responsável:** Software Architect | **Data:** 2026-07-28

## Contexto
Markdown é output aprovado; Business Analyst não pode inventar.
## Problema
Renderizar documentos rastreáveis sem sobrescrita ou variável silenciosa.
## Alternativas
Concatenação; Jinja2; geração livre por IA.
## Decisão
Jinja2 com `StrictUndefined`, templates registrados, dados Pydantic, Markdown no
projeto e manifesto YAML com origem, versão, checksum e producer.
## Justificativa
Jinja2 foi aprovado e oferece templates explícitos; IA externa fica fora.
## Consequências
Templates são contratos versionados; campo ausente falha ou vira pergunta declarada.
## Riscos
Template inseguro/path traversal. Loader restrito, filtros allowlisted e testes.
