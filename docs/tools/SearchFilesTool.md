# SearchFilesTool

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

Pesquisa arquivos seguros dentro do workspace por nome, extensão e/ou texto.

## Contrato

- Tool ID: `search-files`;
- capability: `search`;
- payload: `path` opcional e ao menos um entre `name`, `extension`, `text`;
- output: lista determinística de paths relativos.

Arquivos binários ou ilegíveis são ignorados. Áreas críticas e symlinks
externos não entram na busca. O limite atual é 1.000 resultados.

Referência: [Tool Architecture](ToolArchitecture.md).

