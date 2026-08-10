# Project Workspace Browsing

**Dono:** Engenharia ASEP | **Versão:** 0.1 | **Status:** vigente

## Objetivo e fronteiras

O filesystem de `WorkspaceProject` é a fonte da verdade. O File Explorer é
somente observabilidade read-only: não edita, persiste, executa ou envia arquivos
ao AI Runtime. Ele pertence ao projeto, não a uma `ProjectSession`.

O browser fornece apenas `project_id` e um path relativo. `ProjectService`
resolve a raiz persistida, e `ProjectWorkspaceService` confina toda navegação a
essa raiz. Paths absolutos, UNC, troca de drive, byte nulo, `.`/`..`, escape da
raiz e componentes symlink/reparse point são rejeitados. Symlinks e reparse
points também não aparecem em listagens.

## Política

`WorkspaceBrowsingPolicy` é imutável e centraliza:

- arquivos de até 1 MiB;
- até 1.000 filhos imediatos por diretório;
- exclusão de `.git`, `.ssh`, `__pycache__`, `node_modules`, `.next`,
  `.pytest_cache`, `dist` e `build`;
- bloqueio de `.env`, `.env.*`, `.netrc`, `id_rsa`, `id_ed25519`,
  `credentials*`, `*.pem` e `*.key`.

A listagem é lazy, diretórios precedem arquivos e nomes são ordenados de forma
case-insensitive determinística. Somente texto UTF-8/UTF-8 BOM é exibido. Binário
e arquivo acima do limite falham com erros seguros; nenhum path absoluto retorna
à API. O viewer usa `pre/code`, apresenta path relativo, tamanho, language hint e
indicador Read-only.
