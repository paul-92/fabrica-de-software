# Sprint 7.5 — SQLite Repository

**Público:** iniciantes, pessoas desenvolvedoras e arquitetas  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída

## Visão Geral

Esta é a fotografia arquitetural da Sprint 7.5. Ela adicionou persistência
SQLite para Runs e Timeline sem mudar as portas consumidas pelos serviços.

## O Problema

Memória perde dados ao encerrar o processo. Arquivos JSON são duráveis, porém
reescrevem o documento inteiro. Faltava uma opção local, transacional e
adequada a atualizações e consultas frequentes.

## A Solução

Foram criados `SQLiteRunRepository`, `SQLiteTimelineRepository` e a
infraestrutura compartilhada `SQLiteDatabase`. `RepositoryFactory` seleciona o
backend `sqlite` a partir de `ApplicationSettings`.

## Explicação simples

Run é uma execução; Timeline é seu diário. SQLite é um caderno em tabelas. A
Factory é quem escolhe esse caderno, enquanto os serviços continuam pedindo
apenas “guarde” ou “consulte”.

## Explicação técnica

O módulo `sqlite` usa apenas `sqlite3`. Ele cria e valida duas tabelas. Os
repositories reutilizam `RunCodec` e `TimelineEventCodec`, armazenam JSON em
`payload`, usam chave primária para identidade e índice por `run_id`. Runs
usam upsert; eventos são append-only.

## Componentes envolvidos

- `ApplicationSettings` e `Configuration`;
- `RepositoryFactory` e `RepositoryBundle`;
- portas `RunRepository` e `TimelineRepository`;
- adapters SQLite;
- `SQLiteDatabase`;
- codecs e erros tipados;
- `RunQueryService`, `MetricsService` e Dashboard API como consumidores.

## Fluxo completo

```text
ASEP_* -> Configuration -> ApplicationSettings -> RepositoryFactory
                                                   |
                       +---------------------------+------------------+
                       v                                              v
             SQLiteRunRepository                         SQLiteTimelineRepository
                       +---------------------------+------------------+
                                                   v
                                           SQLiteDatabase -> asep.db
```

O diagrama mostra que configuração decide; Factory constrói; adapters traduzem;
e a infraestrutura compartilhada gerencia banco/schema.

## Dependências

Serviços dependem das portas, nunca de SQLite. Factory conhece adapters.
Adapters conhecem domínio, codecs e `SQLiteDatabase`. A infraestrutura conhece
somente `sqlite3`, filesystem e erros. Veja
[Dependencies](../persistence/Dependencies.md).

## Exemplos

```python
settings = ApplicationSettings(
    storage_backend="sqlite",
    sqlite_database="storage/asep.db",
)
repositories = RepositoryFactory(settings).create()
```

Por ambiente: `ASEP_STORAGE_BACKEND=sqlite` e
`ASEP_SQLITE_DATABASE=storage/asep.db`.

## Testes

Testes próprios cobrem criação, schema, persistência, upsert, corrupção e
integração. Testes de contrato executam contra memory, file e sqlite. Evidência
no encerramento da Sprint: `600 passed`, `compileall` aprovado e diff limpo.

## Erros comuns

Backend com caixa errada gera configuração inválida; caminho para diretório
gera erro de conexão; banco com schema divergente gera `SQLiteSchemaError`;
evento repetido gera `DuplicateTimelineEventError`. Preserve bancos inválidos
antes de investigar.

## Limitações

Sem ORM, pool, migrations versionadas, retry, backup automático, paginação ou
transação coordenada entre Run e Timeline. O backend padrão permanece memory.

## Evolução futura

Evoluções possíveis — não implementadas nesta Sprint — exigem decisão própria:
versionamento/migrations, backup, observabilidade, tuning e outros bancos.

## Referências

- [Repositórios](../persistence/SQLiteRepositories.md)
- [Schema](../persistence/DatabaseSchema.md)
- [Arquitetura](../persistence/SQLiteArchitecture.md)
- [Configuração](../persistence/SQLiteConfiguration.md)

## Relacionado a

- Sprint 7.5; [Fase 07](../history/Phase-07.md)
- [ADR-016](../adr/ADR-016-sqlite-persistence.md)
- componentes `configuration`, `repositories`, `runs`, `timeline`, `sqlite`
- testes `test_sqlite_repository.py` e contratos de repositories
- [Roadmap](../architecture/Roadmap.md)
- [Architecture v1](../architecture/ASEP-Architecture-v1.md)
- [Glossário de persistência](../glossary/PersistenceGlossary.md)
