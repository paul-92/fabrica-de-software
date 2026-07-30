# Detecção de arquitetura

**Público:** arquitetura e engenharia  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

O detector reconhece evidências para MVC, Clean Architecture, Hexagonal,
Onion, Monolith, Library, CLI, REST API, Desktop e Web Application.

Regras usam nomes de diretórios, manifests, entrypoints e frameworks já
detectados. Resultados podem coexistir: por exemplo, um monólito pode expor
REST API e organizar-se em MVC.

`Monolith` descreve o escopo observado como uma única árvore de projeto; não
afirma ausência de serviços externos. A saída sempre carrega evidências e não
usa pontuação probabilística.
