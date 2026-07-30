# RunTestsTool

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

Executa pytest por um contrato restrito; agentes não montam comandos.

## Contrato

- Tool ID: `run-tests`;
- capability: `test`;
- payload: `paths`, lista opcional de paths existentes no workspace;
- comando fixo: `python -m pytest PATH...`;
- output: exit code, stdout, stderr e comando serializável.

Não são aceitos flags, shell, ambiente customizado ou paths externos. O
processo usa `shell=False`, cwd do workspace, UTF-8 e timeout. Exit code
diferente de zero produz resultado `failed`; timeout produz `timed_out` pelo
serviço de execução.

Referência: [Tool Architecture](ToolArchitecture.md).

