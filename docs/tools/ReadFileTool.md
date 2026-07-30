# ReadFileTool

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

Lê um único arquivo UTF-8 dentro do workspace.

## Contrato

- Tool ID: `read-file`;
- capability: `read_file`;
- payload: `{"path": "path/relativo.txt"}`;
- output: path normalizado e conteúdo.

Paths absolutos, traversal, destinos externos por symlink, áreas críticas,
diretórios e conteúdo não UTF-8 são rejeitados. A Tool não escreve arquivos.

Referência: [Tool Architecture](ToolArchitecture.md).

