# Registry Design

**ID:** ARCH-REG-001 | **Versão:** 0.1.0 | **Status:** approved

## Responsabilidade

Descobrir agentes, contratos, workflows, gates, templates e demais componentes
por ID/version, sem guardar estado de execução.

## Carregamento

1. resolver uma raiz configurada pelo projeto;
2. usar `yaml.safe_load`;
3. validar documento e itens com modelos Pydantic;
4. rejeitar IDs duplicados, versão inválida e campo desconhecido;
5. normalizar caminhos relativos sem permitir saída da raiz;
6. confirmar existência e tipo do destino;
7. resolver referências cruzadas e produzir catálogo imutável;
8. calcular fingerprint das definições fixadas na execução.

## Interface

```text
RegistryPort.load(root) -> RegistrySnapshot
RegistrySnapshot.get(kind, id, version?) -> ComponentRef
RegistrySnapshot.validate_references() -> Findings
```

## Entradas e saídas

Entrada: `registry/*.yaml` e raiz do workspace. Saída: modelos validados, índices
por tipo/ID e lista de findings com código, localização e severidade.

## Erros

`REG_PARSE`, `REG_SCHEMA`, `REG_DUPLICATE_ID`, `REG_PATH_ESCAPE`,
`REG_MISSING_TARGET`, `REG_UNKNOWN_REFERENCE`, `REG_VERSION_MISMATCH`.
Nenhum erro é ignorado; severidade bloqueante impede start.

## Limites

Sem download, descoberta remota, plugin dinâmico ou autoatualização. Cache, se
usado no processo, é descartável e invalidado pelo fingerprint.

## Testes

Fixtures válidas/inválidas, property tests de paths, duplicidade, versão, referência
cruzada e garantia de que load não altera arquivos.
