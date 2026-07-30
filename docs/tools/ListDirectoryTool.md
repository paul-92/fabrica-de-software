# ListDirectoryTool

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

Lista entradas imediatas de um diretório do workspace.

## Contrato

- Tool ID: `list-directory`;
- capability: `directory`;
- payload: `path` relativo opcional, com default `.`;
- output: entries ordenadas com path e tipo `file` ou `directory`.

Entradas críticas e destinos externos são omitidos. A listagem não é recursiva.

Referência: [Tool Architecture](ToolArchitecture.md).

