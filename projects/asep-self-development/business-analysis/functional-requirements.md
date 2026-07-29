# Requisitos Funcionais

**ID:** BA-FR-001 | **Versão:** 0.1.1 | **Status:** Must aprovados; Should/Could candidatos  
**Dono:** Business Analyst | **Data:** 2026-07-28

Os requisitos `Must` materializam o escopo aprovado pelo Product Owner. `Should`
e `Could` não foram adicionados ao compromisso da versão.

| ID | Requisito | Prioridade | Regras | Critério |
|---|---|---|---|---|
| FR-001 | O operador deve criar ou abrir um projeto a partir de um registro identificável. | Must | BR-001 | AC-001 |
| FR-002 | O sistema deve carregar os catálogos do Registry necessários à execução. | Must | BR-010 | AC-002 |
| FR-003 | O sistema deve rejeitar IDs, caminhos ou versões referenciadas que não existam. | Must | BR-001 | AC-003 |
| FR-004 | O sistema deve carregar o contrato versionado do agente atribuído. | Must | BR-002 | AC-004 |
| FR-005 | O operador deve selecionar um workflow aplicável, e o sistema deve validar a seleção. | Must | BR-001 | AC-005 |
| FR-006 | O sistema deve instanciar uma execução com etapas e dependências do workflow. | Must | BR-001 | AC-006 |
| FR-007 | O sistema deve liberar uma etapa sequencial somente após suas predecessoras concluírem. | Must | BR-002 | AC-007 |
| FR-008 | O sistema deve registrar e consultar o estado do projeto. | Must | BR-006 | AC-008 |
| FR-009 | O sistema deve registrar estado e tentativa de cada etapa. | Must | BR-006 | AC-009 |
| FR-010 | O sistema deve validar required inputs antes de iniciar o agente/etapa. | Must | BR-002 | AC-010 |
| FR-011 | O sistema deve registrar artefato com identidade, versão, produtor, origem e estado. | Must | BR-009 | AC-011 |
| FR-012 | O sistema deve avaliar critérios de gate e vincular evidências. | Must | BR-003 | AC-012 |
| FR-013 | O sistema deve pausar quando exigir aprovação humana e registrar a decisão autorizada. | Must | BR-004, BR-005 | AC-013 |
| FR-014 | O sistema deve emitir eventos estruturados para transições relevantes. | Must | BR-006 | AC-014 |
| FR-015 | O sistema deve preservar uma trilha que relacione comando, ator, estado, gate, decisão e artefato. | Must | BR-005 | AC-015 |
| FR-016 | O sistema deve registrar falha com causa e impedir avanço indevido. | Must | BR-006 | AC-016 |
| FR-017 | O operador deve retomar execução bloqueada/falha elegível após revalidação. | Must | BR-008 | AC-017 |
| FR-018 | O operador autorizado deve cancelar e preservar o histórico da execução. | Must | BR-007 | AC-018 |
| FR-019 | As capacidades do MVP devem ser acessíveis por CLI em execução local. | Must | — | AC-019 |
| FR-020 | O fluxo essencial deve funcionar sem chamada obrigatória a provedor externo de IA. | Must | BR-012 | AC-020 |
| FR-021 | O operador deve consultar projeto, execução e etapas sem alterar estado. | Should | BR-006 | AC-021 |
| FR-022 | O sistema pode recomendar workflows por classificação, exigindo confirmação. | Could | BR-004 | AC-022 |

## Fora do MVP

Execução paralela, interface gráfica, serviço remoto e execução autônoma de
especialistas não são requisitos do MVP candidato.
