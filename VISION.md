# Visão da AI Software Engineering Platform — ASEP

**Dono:** Product Manager da ASEP  
**Versão:** 0.1.0  
**Status:** proposta para validação  
**Última revisão:** 2026-07-28

## Visão do produto

A ASEP será um sistema operacional organizacional, legível por pessoas e agentes de IA, para transformar demandas de software em entregas governadas, verificáveis, seguras e transferíveis. A plataforma coordena papéis, contratos, workflows, evidências, decisões e aprendizado sem substituir a autoridade humana.

## Problema resolvido

Equipes que usam agentes de IA frequentemente operam com prompts isolados, contexto inconsistente, responsabilidades sobrepostas e pouca evidência de qualidade. A ASEP fornece linguagem comum, interfaces explícitas e gates verificáveis para reduzir perda de contexto, decisões implícitas, retrabalho e risco.

## Público-alvo

- organizações de desenvolvimento de software assistido por IA;
- consultorias e software houses com múltiplos clientes;
- equipes de produto e engenharia que precisam de governança auditável;
- responsáveis por produto, entrega, arquitetura, qualidade, segurança e operação.

## Proposta de valor

Uma demanda entra uma vez, é classificada, percorre um workflow adequado, recebe especialistas sob contratos versionados e produz artefatos rastreáveis. Pessoas mantêm as decisões materiais; agentes aceleram análise e execução dentro de limites explícitos.

## Objetivos

1. Padronizar o ciclo de vida sem impor uma stack universal.
2. Tornar entradas, saídas, responsabilidades e aprovações verificáveis.
3. Permitir composição segura de agentes e workflows.
4. Preservar memória organizacional validada sem misturar dados de clientes.
5. Preparar especificação implementável para Orchestrator e Runtime futuros.

## Escopo da versão 1.0

- governança, lifecycle, quality gates e protocolo de handoff;
- catálogo de agentes, papéis, departamentos, contratos e componentes;
- workflows declarativos para tipos de projeto suportados;
- playbooks, standards, knowledge base e templates fundamentais;
- estruturas de clientes, projetos, memória e observabilidade;
- especificação conceitual de Orchestrator e Runtime;
- projeto piloto de autodesenvolvimento e validações documentais.

## Fora do escopo

- execução autônoma em produção;
- integração real com APIs de modelos, ferramentas externas ou sistemas de clientes;
- IDE, interface web, motor de workflow ou armazenamento operacional;
- stack obrigatória para projetos derivados;
- requisitos definitivos do projeto piloto.

## Princípios inegociáveis

- fatos, hipóteses, decisões e evidências são distinguíveis;
- agentes não inventam requisitos nem aprovações;
- decisões materiais e riscos residuais têm dono humano;
- segurança, privacidade, acessibilidade e operação são contínuas;
- nenhum gate é aprovado sem evidência;
- artefatos são portáveis, versionados e localizáveis;
- dados de clientes não entram na memória global.

## Indicadores de sucesso

| Indicador | Evidência na 1.0 |
|---|---|
| Integridade do catálogo | 100% dos caminhos registrados existem |
| Compatibilidade | Contratos têm entradas/saídas encadeáveis e sem ciclos acidentais |
| Qualidade documental | Links internos e YAML validados automaticamente |
| Governança | Gates e aprovações possuem critérios, evidências e autoridade |
| Usabilidade | Um projeto novo pode ser iniciado pelo template e workflow sem conhecimento tácito |
| Rastreabilidade | Artefatos, decisões e eventos possuem identificadores e origem |

## Limitações atuais

A versão atual é documental e declarativa. Não existe motor de execução, persistência de estado, autenticação, UI ou integração com modelos. Métricas de eficácia dependem do projeto piloto. Autoridades organizacionais precisam ser nomeadas pela organização adotante.

## Roadmap de alto nível

Fundação documental → Registry e contratos → workflows declarativos → Orchestrator mínimo → Runtime de agentes → projeto piloto → versão 1.0 utilizável. Detalhes em [planning/ROADMAP.md](planning/ROADMAP.md).
