# Escopo

**ID:** BA-SCP-001 | **Versão:** 0.1.1 | **Status:** aprovado pelo Product Owner  
**Dono:** Business Analyst | **Data:** 2026-07-28

## Escopo aprovado da versão 0.1

- criar/abrir projeto a partir de metadados válidos;
- carregar Registry, contratos e workflow versionados;
- validar referências e entradas obrigatórias;
- instanciar execução e etapas sequenciais;
- manter estados de projeto, etapa e tentativa;
- registrar artefatos e evidências;
- avaliar quality gates e solicitar aprovação humana;
- registrar logs e trilha de auditoria;
- tratar falha, retomada e cancelamento;
- operar localmente por CLI sem provedor externo obrigatório.

Os componentes aprovados são: Registry, Workflow Engine, Runtime, Orchestrator,
Business Analyst, geração de artefatos Markdown, Logging e Quality Gates.

## Fora do MVP candidato

- execução paralela;
- interface gráfica;
- serviço remoto multiusuário;
- integração obrigatória com modelos de IA;
- autenticação;
- banco de dados;
- dashboard;
- multiusuário;
- substituição da stack aprovada sem change request;
- implementação de código durante Business Analysis/Architecture;
- execução de deploy de produtos;
- edição visual de Registry/workflows;
- autonomia para aprovar gates ou decisões humanas.

## Aprovação

Paulo Cesar, Product Owner e autoridade de Escopo, aprovou esta baseline em
2026-07-28. Alterações posteriores seguem controle de mudança.

## Controle de mudança

Alteração material segue [core/CHANGE-MANAGEMENT.md](../../../core/CHANGE-MANAGEMENT.md)
e atualiza requisitos, prioridades, riscos e critérios relacionados.
