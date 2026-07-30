# Heurísticas do Project Analyzer

**Público:** QA, arquitetura e mantenedores  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Linguagens e linhas

Extensões conhecidas identificam Python, JavaScript, TypeScript, Java, Kotlin,
C#, Go, Rust, PHP e Ruby. Linhas são contadas em arquivos reconhecidos, com
UTF-8 e substituição de bytes inválidos.

## Dependências e gerenciadores

São lidos `pyproject.toml`, `requirements.txt` e `package.json`.
Gerenciadores também são inferidos por lockfiles/manifests de pip, Poetry,
Pipenv, npm, pnpm e Yarn. Apenas dependências diretas são reportadas.

## Módulos, testes e documentação

Diretórios de primeiro nível, exceto `tests` e `docs`, e fontes na raiz são
módulos. Testes usam convenções `test_`, `.test.*`, `.spec.*` e diretório
`tests`. Markdown/RST e nomes documentais conhecidos contam como documentação.

## Determinismo

Scanner, modelos e coleções usam ordem explícita. Duas análises do mesmo
conteúdo produzem os mesmos dados, exceto `generated_at`.

## Limitações

- aliases de import e configuração dinâmica podem não ser reconhecidos;
- monorepos não são segmentados automaticamente;
- arquivos ilegíveis não contribuem para linhas;
- não há parsing semântico de AST de cada linguagem;
- não há IA, embeddings, geração ou integração externa.
