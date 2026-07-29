# Artifact Management

**ID:** ARCH-ART-001 | **Versão:** 0.1.0 | **Status:** approved

## Responsabilidade

Gerar e registrar Markdown a partir de templates e dados validados, preservando
origem, versão e checksum. Não interpreta requisito nem aprova conteúdo.

## Estrutura

```text
projects/<id>/<phase>/<artifact>.md
projects/<id>/.asep/artifacts/<artifact-id>.yaml
```

O manifesto contém ID, tipo, versão, status, producer, source IDs, template
version, relative path, classification, SHA-256 e timestamps.

## Renderização

Jinja2 em ambiente restrito com `StrictUndefined`, autoescape não aplicável a
Markdown mas filtros permitidos explícitos. Templates vêm do Registry; includes
não podem sair da raiz. Dados são modelos Pydantic, não dicionários arbitrários.

## Escrita

Renderizar em memória → validar conteúdo/metadados → escrever temporário no mesmo
diretório → flush → replace → registrar manifesto. Colisão exige versão nova ou
comando explícito; nunca sobrescrever silenciosamente.

## Business Analyst Adapter

Gera estrutura e conteúdo somente a partir de fatos/decisões fornecidos. Campo
ausente vira finding ou pergunta com dono; nunca texto plausível inventado.

## Testes

Golden files, missing variable, path traversal, colisão, Unicode, checksum,
write failure e idempotência.
