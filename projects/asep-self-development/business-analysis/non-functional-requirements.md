# Requisitos Não Funcionais

**ID:** BA-NFR-001 | **Versão:** 0.1.1 | **Status:** baseline parcial aprovada  
**Dono:** Business Analyst | **Data:** 2026-07-28

| ID | Requisito verificável | Prioridade | Critério |
|---|---|---|---|
| NFR-001 | Toda transição deve ser rastreável à execução, ator, versão e momento. | Must | AC-NF-001 |
| NFR-002 | Interrupção ou falha não pode produzir estado parcialmente apresentado como concluído. | Must | AC-NF-002 |
| NFR-003 | Logs e artefatos não devem expor segredos ou dados pessoais desnecessários. | Must | AC-NF-003 |
| NFR-004 | Comandos devem informar resultado, erro acionável e próxima ação sem exigir inspeção de implementação. | Must | AC-NF-004 |
| NFR-005 | A especificação não deve acoplar o uso a um provedor externo; ambientes locais suportados serão definidos posteriormente. | Should | AC-NF-005 |
| NFR-006 | Falhas devem possuir código/categoria, contexto de correlação e causa preservada de forma segura. | Must | AC-NF-006 |
| NFR-007 | Execução deve fixar versões dos componentes e detectar incompatibilidade antes do estágio afetado. | Must | AC-NF-007 |
| NFR-008 | Metas de tempo e volume devem ser definidas após conhecer cenário e ambiente do piloto. | pendente | AC-NF-008 |

## Lacunas deliberadas

Não foram inventados targets de latência, capacidade, disponibilidade, sistemas
operacionais suportados, retenção ou criptografia. Essas medidas dependem de
contexto, risco e decisões posteriores.

## Temas para especialistas

Security deverá validar classificação, identidade e retenção; QA definirá a
estratégia; Architecture avaliará opções somente depois do gate de análise.
