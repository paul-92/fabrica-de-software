# Auditoria de testes — RC1

**Dono:** QA ASEP | **Versão:** 1.0 | **Status:** concluída em 2026-07-30

## Resultado

- 665 testes aprovados;
- 41 módulos `test_*.py`, além de fixtures e probes de QA;
- cobertura total: **95%** (`4777` statements, `261` não cobertos);
- tempo observado: 17,68 s sem cobertura e 20,50 s com cobertura;
- testes usam fakes e diretórios temporários; Codex real não é necessário.

## Áreas de menor cobertura

| Módulo | Cobertura |
|---|---:|
| `providers/process.py` | 68% |
| `runs/sqlite_repository.py` | 73% |
| `timeline/sqlite_repository.py` | 73% |
| `workflow_persistence/sqlite_repository.py` | 78% |
| `workflow/loader.py` | 79% |

São principalmente ramos de falha de sistema operacional/SQLite. Não foi
adicionado teste artificial apenas para elevar percentual.

## Qualidade e isolamento

- contratos de Run, Timeline e Workflow Persistence são exercitados por backend;
- Registry e repositories são instanciados por teste, sem singleton;
- CLI/API possuem integração;
- Timeline/Metrics e falhas de workflow têm regressão;
- nenhum teste útil foi removido.

## Achados

O `%TEMP%` desta máquina apresenta diretórios antigos sem permissão. O comando
confiável usa `--basetemp` em diretório local ignorado. Isso é risco ambiental,
não falha funcional.

As três conexões não fechadas em fixtures SQLite foram corrigidas. A repetição
com `ResourceWarning` e tracemalloc não apontou vazamento de produção.

## Pendências

- não existe threshold de cobertura configurado;
- arquivos de testes grandes podem ser subdivididos quando forem alterados;
- CI remoto ainda precisa confirmar Windows e, idealmente, Linux/macOS.

