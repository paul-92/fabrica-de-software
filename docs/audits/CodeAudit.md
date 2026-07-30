# Auditoria de código — RC1

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída em 2026-07-30

## Método

Inspeção por `rg`, AST, compilação, cobertura e revisão dos maiores arquivos.
Sem linter/type checker configurado, não se declara ausência absoluta de imports
inutilizados.

## Achados

- nenhum `TODO`, `FIXME`, `HACK` ou `NotImplementedError` em produção;
- `pass` em exceções vazias é intencional;
- `pass` em limpeza de temporários preserva o erro original;
- `pass` em CLI/state pertence a cleanup best-effort;
- nenhum componente órfão foi confirmado por evidência;
- zero ciclos internos de imports;
- 250 classes e 438 funções/métodos detectados.

## Tamanho e complexidade

Maiores arquivos de produção:

| Arquivo | Linhas | Classificação |
|---|---:|---|
| `orchestrator/service.py` | 565 | alto, dívida conhecida |
| `application/stage_execution.py` | 424 | alto |
| `execution_graph/builder.py` | 403 | médio-alto |
| `exporters/bpmn.py` | 390 | médio-alto |
| `cli.py` | 383 | médio-alto |

Não foram feitas extrações apenas para reduzir linhas, conforme KISS/YAGNI.

## Correção realizada

Três testes SQLite deixavam conexões para o garbage collector porque
`sqlite3.Connection.__exit__` encerra transação, mas não fecha a conexão. As
fixtures agora usam `contextlib.closing`. O comportamento de produção não foi
alterado.

## Pendências

- configurar linter e type checker exige decisão futura, não foi introduzido;
- priorizar testes antes de refatorar arquivos grandes;
- avaliar utilitário comum de escrita atômica em Sprint técnica própria.

