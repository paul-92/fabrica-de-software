# Dependências da persistência SQLite

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

## Visão Geral

Este mapa define quem pode conhecer quem na persistência da Sprint 7.5.

## O Problema

Se serviços conhecerem SQL/adapters, trocar backend quebra consumidores e
espalha infraestrutura pela aplicação.

## A Solução

Aplicar inversão de dependência: consumidores conhecem portas; o composition
root escolhe adapters.

## Explicação simples

O atendente pede uma gaveta, não uma gaveta SQLite. Só o responsável pelo
almoxarifado sabe qual modelo foi escolhido.

## Explicação técnica

```text
API/CLI composition -> Configuration -> RepositoryFactory
Services -----------------------------> Repository Protocols
RepositoryFactory --------------------> SQLite adapters
SQLite adapters -> Domain + Codecs + SQLiteDatabase
SQLiteDatabase -----------------------> sqlite3 + Path
```

Setas significam “pode depender de”.

## Componentes envolvidos

Configuration, Factory, protocols, adapters, codecs, conexão, serviços e API.

## Fluxo completo

Configuração entra pela composição; Factory entrega portas; serviços consultam
portas; adapters serializam e chamam a conexão; conexão opera `asep.db`.

## Dependências

Obrigatórias: biblioteca padrão, modelos/codecs e portas. Opcionais: backend
selecionado. Proibidas: serviços/API dentro de adapters; SQLite dentro de
serviços; Factory dentro de modelos; repositories concretos dentro da API.

## Exemplos

Correto: `RunQueryService(run_repository: RunRepository, ...)`.
Incorreto: construir `SQLiteRunRepository` dentro do serviço.

## Testes

`test_repository_factory.py` procura construções concretas fora da Factory.
Testes dos serviços confirmam ausência de imports concretos.

## Erros comuns

Importar adapter “por conveniência” viola a fronteira. Mover SQL para serviço
duplica tratamento e impede testes com memory.

## Limitações

O controle é feito por testes/inspeção, não por ferramenta de arquitetura.

## Evolução futura

Um verificador estático pode formalizar camadas quando o projeto crescer.

## Referências

[Architecture](SQLiteArchitecture.md) e
[Architecture Map](../architecture/ArchitectureMap.md).

## Relacionado a

Sprint 7.5; Fase 07; ADR-016; RepositoryFactory; testes arquiteturais;
[Roadmap](../architecture/Roadmap.md);
[Glossário](../glossary/PersistenceGlossary.md).
