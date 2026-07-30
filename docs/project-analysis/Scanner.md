# Project Scanner

**Público:** mantenedores do Project Analyzer  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

`ProjectScanner` percorre a árvore com ordem determinística, preserva caminhos
relativos e calcula profundidade. Arquivos e diretórios ocultos são ignorados.

Diretórios ignorados por padrão:

```text
.git .idea .vscode node_modules __pycache__ dist build
.venv venv coverage .pytest_cache
```

A lista pode ser substituída no construtor. Erro de `stat` em um arquivo não
interrompe toda a análise. Symlinks de diretório não são seguidos pelo
`os.walk`, evitando ciclos por padrão.
