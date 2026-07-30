# ReadDocumentationTool

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

Lê arquivos UTF-8 exclusivamente sob o diretório `docs/` do workspace.

## Contrato

- Tool ID: `read-documentation`;
- capability: `documentation`;
- payload: `{"path": "guia.md"}`, relativo a `docs/`;
- output: path relativo ao workspace e conteúdo.

Traversal, paths absolutos, áreas críticas, diretórios, symlinks externos e
conteúdo não UTF-8 são rejeitados.

Referência: [Tool Architecture](ToolArchitecture.md).
