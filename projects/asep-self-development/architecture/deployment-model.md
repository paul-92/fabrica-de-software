# Deployment Model

**ID:** ARCH-DEP-001 | **Versão:** 0.1.0 | **Status:** approved

## Modelo local

Um pacote Python instala o comando `asep` em ambiente isolado local compatível com
Python 3.12+. Não há servidor, container, banco, daemon ou infraestrutura remota.
O método concreto de empacotamento/distribuição será selecionado no planejamento
sem adicionar dependência runtime.

## Diretórios

```text
workspace/
  registry/ contracts/ workflows/ templates/
  projects/<id>/
    project.yaml
    .asep/state.yaml
    .asep/artifacts/*.yaml
    .asep/audit/events.jsonl
    .asep/logs/execution.jsonl
    <phase>/*.md
```

Configuração explícita aponta a raiz. O aplicativo não escreve em diretórios
globais por padrão.

## Compatibilidade e upgrade

CLI, schemas e state snapshot têm versão. Ao abrir versão futura, ferramenta
rejeita incompatibilidade e recomenda migração; migração automática não entra
na 0.1. Backup é cópia consistente do projeto quando não houver lock ativo.

## Operação

Pré-condições: ambiente aprovado, permissões locais e workspace válido. Rollback
do executável reinstala versão anterior; dados só reabrem se schema compatível.
Matriz oficial de sistemas operacionais permanece pergunta de produto.
