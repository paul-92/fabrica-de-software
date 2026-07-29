$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Write-Doc {
    param([string]$Path, [string]$Content)
    $target = Join-Path $Root $Path
    $dir = Split-Path -Parent $target
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $normalized = ($Content.Trim() + "`n")
    [System.IO.File]::WriteAllText($target, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function Add-Doc {
    param([string]$Path, [string]$Content)
    $target = Join-Path $Root $Path
    if (-not (Test-Path -LiteralPath $target)) { Write-Doc $Path $Content }
}

$date = "2026-07-28"

Write-Doc "VISION.md" @'
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
'@

Write-Doc "README.md" @'
# AI Software Engineering Platform — ASEP

**Versão documental:** 0.1.0  
**Status:** fundação documental utilizável; Runtime e Orchestrator ainda são especificações  
**Dono:** Product Manager da ASEP

A ASEP é um sistema operacional organizacional para desenvolvimento de software assistido por agentes de IA. Ela combina governança, ciclo de vida, especialistas, contratos, workflows, qualidade, memória e observabilidade. Não é uma coleção de prompts e não executa modelos de IA nesta versão.

## Como funciona

Uma demanda é registrada pelo Intake, classificada pelo Orchestrator e associada a um workflow. Cada etapa recebe agentes cujo contrato declara entradas, saídas, limites e gates. Artefatos permanecem no projeto; decisões duráveis usam ADR; aprovações humanas e eventos mantêm a rastreabilidade. O funcionamento central está em [core/SYSTEM.md](core/SYSTEM.md).

## Estrutura principal

| Área | Responsabilidade |
|---|---|
| `core/` | funcionamento, governança, lifecycle, qualidade e segurança |
| `roles/`, `departments/` | autoridade organizacional e especialidades |
| `agents/`, `contracts/` | comportamento e interfaces dos agentes |
| `registry/` | catálogo e descoberta dos componentes |
| `workflows/` | ordem, condições, gates e aprovações |
| `playbooks/` | procedimentos operacionais |
| `knowledge/` | conhecimento de negócio e engenharia |
| `standards/` | regras obrigatórias, recomendações e exceções |
| `templates/` | modelos de artefatos |
| `clients/`, `projects/` | contexto segregado de clientes e iniciativas |
| `memory/` | aprendizado global validado |
| `observability/` | eventos, métricas, auditoria e status |
| `orchestrator/`, `runtime/` | especificação da execução futura |
| `planning/`, `reports/` | evolução da plataforma e auditoria |

## Fluxo de um projeto

Intake → Discovery → Business Analysis → Architecture → Planning → Design → Implementation → Review → Testing → Security → Deployment → Documentation → Handover → Maintenance → Retrospective. Etapas podem ser condicionais ou paralelas conforme o workflow, mas gates não são omitidos.

## Como iniciar

1. Leia [VISION.md](VISION.md), [AGENTS.md](AGENTS.md) e [core/SYSTEM.md](core/SYSTEM.md).
2. Copie `clients/_template/` se houver novo cliente.
3. Copie `projects/_template/` e preencha `project.yaml` e o Project Brief.
4. Execute [workflows/project-intake.md](workflows/project-intake.md).
5. Selecione um workflow registrado em [registry/workflows.yaml](registry/workflows.yaml).
6. Registre decisões materiais em `projects/<id>/decisions/`.

## Como criar um novo agente

Use [templates/agent.md](templates/agent.md), mantenha as 27 seções obrigatórias, crie o contrato correspondente, registre ambos em `registry/agents.yaml` e `registry/contracts.yaml`, valide conflitos de autoridade e obtenha aprovação conforme [core/GOVERNANCE.md](core/GOVERNANCE.md).

## Como criar um novo workflow

Use um workflow YAML existente como referência, declare dependências, condições, gates, aprovações, artefatos e falhas; registre em `registry/workflows.yaml`; valide agentes e gates; aprove a mudança segundo [core/CHANGE-MANAGEMENT.md](core/CHANGE-MANAGEMENT.md).

## Como criar um novo projeto

Copie `projects/_template/`, atribua ID único em `kebab-case`, escolha `project_type` e `workflow_id` existentes, mantenha artefatos no próprio projeto e use `artifacts/` apenas para ativos globais aprovados.

## Navegação complementar

O material anterior útil foi preservado em `docs/`, `prompts/` e nos playbooks por tipo de produto. O glossário canônico está em [docs/glossary.md](docs/glossary.md). Decisões humanas abertas estão em [reports/open-decisions.md](reports/open-decisions.md).
'@

Write-Doc "MANIFESTO.md" @'
# Manifesto da ASEP

**Status:** ativo  
**Dono:** Executive  
**Revisão:** 2026-07-28

1. Problemas antes de funcionalidades.
2. Evidência antes de convicção.
3. Fatos separados de hipóteses.
4. Responsabilidade humana antes de autonomia irrestrita.
5. Entregas pequenas antes de apostas irreversíveis.
6. Clareza e rastreabilidade antes de velocidade aparente.
7. Qualidade, segurança, privacidade, acessibilidade e operação desde o início.
8. Contratos explícitos antes de handoffs informais.
9. Simplicidade sustentável antes de novidade tecnológica.
10. Aprendizado validado antes de memória permanente.

## Como trabalhamos

Tornamos objetivos, restrições, incertezas e trade-offs explícitos; produzimos evidência utilizável; projetamos caminhos de falha e recuperação; documentamos o suficiente para decidir, operar e transferir; contestamos solicitações incompatíveis com o objetivo ou com a segurança.

## Compromissos com clientes

Transparência sobre progresso, risco, custo e incerteza; portabilidade dos ativos; proteção de dados; uso autorizado de IA; aprovações materiais por pessoas responsáveis; handover sem dependência artificial.

## O que não fazemos

Não inventamos requisitos, pesquisas, testes ou aprovações; não usamos dark patterns; não registramos segredos; não publicamos sem rollback e responsáveis; não transferimos risco silencioso; não colocamos dados de clientes na memória global.
'@

Write-Doc "COMPANY.md" @'
# Modelo Organizacional da ASEP

**Dono:** Executive  
**Status:** ativo  
**Versão:** 0.1.0

## Propósito

Operar desenvolvimento de software assistido por IA com responsabilidade humana, especialização, rastreabilidade e qualidade verificável.

## Serviços e tipos de projeto

A ASEP suporta discovery, web, mobile, SaaS, APIs, integrações, automações, soluções com IA, modernização e manutenção. O enquadramento detalhado permanece em [docs/service-catalog.md](docs/service-catalog.md); nenhuma categoria impõe uma stack.

## Modelo operacional

O Orchestrator coordena fluxo e evidência; especialistas mantêm autoridade de domínio; Product Manager decide valor, prioridade e aceite; Tech Lead arbitra decisões técnicas; Quality Lead avalia evidência e risco residual; Security pode bloquear risco inaceitável; Sponsor decide orçamento, contrato e impacto material.

## Organização

Papéis estão definidos em `roles/`, áreas em `departments/`, agentes em `agents/` e interfaces em `contracts/`. A matriz formal de autoridade está em [core/ORGANIZATION.md](core/ORGANIZATION.md).

## Portfólio e capacidade

- uma prioridade crítica por equipe;
- capacidade explícita para qualidade, dívida e manutenção;
- throughput, lead time, estabilidade e resultado, nunca linhas de código;
- iniciativas sem hipótese, sponsor ou decisão disponível são reformuladas ou suspensas.

## Cadência e métricas

Planejamento de portfólio mensal, planejamento de entrega semanal, sincronização operacional conforme necessidade, review por marco, revisão operacional mensal e retrospectiva por ciclo. Toda métrica tem definição, fonte, baseline, alvo, frequência e dono.
'@

Write-Doc "STACK.md" @'
# Política de Stack Tecnológica

**Dono:** Tech Lead  
**Status:** ativo  
**Versão:** 0.1.0

A ASEP não fixa stack universal. Cada projeto registra escolhas, versões, alternativas e estratégia de saída em seu documento de arquitetura e ADRs.

## Critérios de decisão, em ordem

1. requisitos funcionais e atributos de qualidade;
2. segurança, privacidade, acessibilidade e suporte;
3. capacidade da equipe e manutenção;
4. operabilidade, observabilidade e recuperação;
5. custo total, portabilidade e lock-in;
6. maturidade do ecossistema;
7. velocidade inicial.

## Guardrails

- tecnologia crítica precisa de dono, versão suportada e política de atualização;
- novidade material exige alternativas, riscos, PoC limitada quando necessário e ADR;
- dados sensíveis só usam serviços avaliados e autorizados;
- credenciais ficam em cofre aprovado;
- duplicação de ferramentas exige justificativa;
- decisão tecnológica não pode antecipar requisitos ainda não validados.

## Ciclo de vida

Componentes recebem estado `adopt`, `trial`, `assess` ou `hold`. Projetos revisam suporte, vulnerabilidades, licenças, custo e dependências abandonadas. O padrão aplicável está em [standards/versioning.md](standards/versioning.md) e [standards/architecture.md](standards/architecture.md).
'@

Write-Doc "WORKFLOW.md" @'
# Visão Geral dos Workflows

**Dono:** Orchestrator  
**Status:** ativo  
**Versão:** 0.1.0

Workflows definem ordem, paralelismo, condições, retornos, gates, aprovações, bloqueios, cancelamento e retomada. O ciclo de vida canônico está em [core/LIFECYCLE.md](core/LIFECYCLE.md); os workflows executáveis declarativamente ficam em `workflows/*.yaml` e o catálogo em [registry/workflows.yaml](registry/workflows.yaml).

## Regras

1. Toda execução tem projeto, workflow, versão, responsável e estado.
2. Etapa só inicia com dependências e entradas validadas.
3. Paralelismo exige independência explícita e estratégia de reconciliação.
4. Gate exige evidência real; ausência nunca equivale a aprovação.
5. Retorno para correção preserva histórico e motivo.
6. Aprovação humana registra solicitante, autoridade, decisão, data e condições.
7. Bloqueio possui causa, dono e gatilho de retomada.
8. Cancelamento preserva artefatos, auditoria e obrigações de retenção.

## Estados

`planned`, `ready`, `running`, `blocked`, `failed`, `awaiting_approval`, `completed`, `cancelled`. Transições válidas estão em [observability/status-model.md](observability/status-model.md).
'@

Write-Doc "AGENTS.md" @'
# Contrato Operacional dos Agentes ASEP

**Dono:** Orchestrator e responsáveis de domínio  
**Status:** ativo  
**Versão:** 0.1.0

Estas regras valem para agentes humanos ou de IA em projetos ASEP.

## Antes de agir

1. Carregue o brief, contrato, estado, fontes obrigatórias, knowledge e standards aplicáveis.
2. Confirme objetivo, escopo, autoridade, dependências, critérios de aceite e quality gates.
3. Classifique cada afirmação como fato, evidência, hipótese, decisão ou pergunta.
4. Valide entradas; interrompa quando faltar dado crítico.

## Durante o trabalho

- não invente requisitos, fatos, pesquisas, resultados, aprovações ou necessidades;
- declare hipóteses, impacto se falsas, dono e gatilho de validação;
- não invada responsabilidades de outro agente;
- registre decisões duráveis e preserve rastreabilidade;
- produza evidências para cada gate;
- revise o próprio trabalho antes do handoff;
- preserve conteúdo e dados conforme classificação;
- execute apenas mudanças autorizadas e reversíveis quando possível.

## Autoridade e limites

O contrato do agente define autoridade específica. Publicação, gasto, acesso sensível, exclusão material, mudança contratual, decisão de produto de impacto material e aceite de risco alto exigem pessoa autorizada. O Orchestrator coordena, mas não cria requisitos, decide arquitetura sozinho, implementa código, substitui especialistas nem aprova a própria entrega em conflito de interesse.

## Saída e handoff obrigatórios

Toda entrega informa: contexto; objetivo; entradas; validações; trabalho; artefatos/evidências; fatos e hipóteses; decisões; riscos; pendências; checklist; próxima ação; responsável; prazo ou gatilho. Use [core/COMMUNICATION.md](core/COMMUNICATION.md).

## Definition of Done documental

- objetivo, público, dono, versão e status claros;
- termos consistentes com o glossário;
- links internos válidos;
- checklists verificáveis;
- nenhum placeholder silencioso, segredo ou dado pessoal desnecessário;
- decisões e exceções registradas;
- localização acessível pelo README ou Registry.

## Escalonamento

Interrompa e siga [core/ESCALATION.md](core/ESCALATION.md) diante de falta de autorização, contradição crítica, risco alto, conflito de autoridade ou evidência insuficiente.
'@

$core = @{
"core/SYSTEM.md" = @'
# Sistema ASEP

**Dono:** Orchestrator; **status:** ativo; **versão:** 0.1.0

Este é o documento central da plataforma. A ASEP recebe uma demanda, cria um registro de projeto, seleciona workflow e agentes via Registry, valida contratos e conduz estágios até encerramento verificável.

## Fluxo operacional

1. **Receber:** registrar origem, sponsor, problema, urgência, restrições, classificação de dados e autorização.
2. **Criar tarefas:** decompor o workflow em tarefas com ID, objetivo, entradas, saída, agente, dependências, gate e estado.
3. **Selecionar:** consultar capacidades, tipo de projeto, contrato, conflitos, disponibilidade e segregação de funções no Registry.
4. **Validar entradas:** schema, existência, versão, autorização, consistência e suficiência; lacunas viram bloqueio ou hipótese explícita conforme criticidade.
5. **Executar:** seguir lifecycle do agente e playbook aplicável, preservando eventos e artefatos.
6. **Revisar:** auto-review, revisão independente proporcional ao risco e quality gate com evidências.
7. **Aprovar:** pessoa com autoridade decide quando o contrato ou gate exigir; conflito de interesse impede autoaprovação.
8. **Encerrar tarefa:** confirmar saídas, handoff, eventos, decisões, pendências e atualização de estado.
9. **Tratar falhas:** classificar erro, preservar contexto, tentar correção segura, bloquear ou escalar; nunca ocultar falha.
10. **Solicitar decisão humana:** apresentar contexto, alternativas, impacto, recomendação, urgência e prazo.
11. **Armazenar:** artefatos específicos ficam no projeto; reutilizáveis aprovados em `artifacts/`; decisões em `decisions/`; aprendizado validado em `memory/`.
12. **Melhorar:** retrospectivas propõem mudanças; governança aprova; versão e catálogo são atualizados.

## Regras de composição

Contratos são interfaces; workflows são a ordem; agents definem comportamento; standards definem qualidade; knowledge informa decisões; playbooks orientam procedimento; Registry descobre componentes; Observability registra execução.

## Fonte de verdade

O projeto guarda o estado da iniciativa. Registry guarda catálogo, não estado de execução. Memory guarda apenas aprendizado global validado. Em conflito, prevalecem: autorização humana e lei → Core/Governance → contrato versionado → workflow → standards → playbook/knowledge.
'@
"core/LIFECYCLE.md" = @'
# Ciclo de Vida

**Dono:** Delivery Lead; **status:** ativo

| Fase | Resultado verificável | Gate mínimo |
|---|---|---|
| Intake | demanda e autoridade registradas | brief identificável |
| Discovery | problema e evidência compreendidos | hipótese e decisão de avançar |
| Business Analysis | requisitos e regras rastreáveis | validação de stakeholders |
| Architecture | solução e trade-offs | ADRs e riscos aprovados |
| Planning | incrementos, dependências e capacidade | plano executável |
| Design | jornadas e estados validados | acessibilidade e aceite |
| Implementation | incremento integrado | review e checks |
| Review | mudança independente revisada | achados resolvidos/aceitos |
| Testing | riscos cobertos por evidência | critérios e regressão |
| Security | ameaças e controles avaliados | bloqueadores ausentes |
| Deployment | release observável e reversível | go/no-go humano |
| Documentation | documentação atualizada | leitores e operação cobertos |
| Handover | responsabilidade transferida | aceite de recebimento |
| Maintenance | serviço sustentável | SLOs e runbook |
| Retrospective | aprendizado e ações | donos e prazos |

Fases podem ser combinadas em projetos pequenos, nunca omitindo seus resultados e gates. Retorno para correção preserva versão e histórico.
'@
"core/ORGANIZATION.md" = @'
# Organização e Autoridade

**Dono:** Executive; **status:** ativo

| Decisão | Accountable | Consultados | Aprovação humana |
|---|---|---|---|
| valor, prioridade, aceite | Product Manager | Business, Design, Delivery | Sponsor quando material |
| arquitetura e stack | Tech Lead/Architect | Engineering, Security, Operations | sim se irreversível/alto risco |
| estratégia de qualidade | Quality Lead | Product, Engineering | risco residual material |
| segurança e privacidade | Security | Architect, Legal/Privacy | risco alto |
| release | Product + Operations | Quality, Security | sempre para produção |
| fluxo e bloqueios | Delivery Lead/Orchestrator | donos de estágio | quando muda compromisso |

`roles/` define papéis; `departments/` agrupa competências; `agents/` implementa especialidades. Um agente pode recomendar fora de seu domínio, mas não decidir por ele.
'@
"core/COMMUNICATION.md" = @'
# Protocolo de Comunicação e Handoff

**Dono:** Delivery Lead; **status:** ativo

Todo handoff contém: contexto; entradas recebidas; validações realizadas; trabalho executado; artefatos produzidos; fatos e hipóteses; riscos; pendências; decisões necessárias; checklist; recomendação ao próximo agente; responsável e gatilho.

O receptor confirma recebimento, compatibilidade do contrato e lacunas. Decisões materiais não ficam apenas em chat. Bloqueios são comunicados com impacto e opção de retomada. Use `templates/documentation/handover.md`.
'@
"core/DECISIONS.md" = @'
# Decisões e ADR

**Dono:** Tech Lead para ADRs; dono do domínio para demais decisões

Um ADR contém ID e título, contexto, problema, alternativas, decisão, justificativa, consequências, riscos, responsáveis, data e status (`proposed`, `accepted`, `superseded`, `deprecated`). Decisões difíceis de reverter, transversais, caras ou que criam exceção exigem ADR. Nunca reescreva decisão aceita: crie ADR sucessor e vincule o anterior. Template: `templates/architecture/adr.md`.
'@
"core/QUALITY.md" = @'
# Quality Gates

**Dono:** Quality Lead; **status:** ativo

Gates usam critérios observáveis, não percentuais subjetivos. Cada gate registra ID, critérios, evidências, avaliador, decisão, data, achados e exceções.

| Gate | Critérios verificáveis | Evidência obrigatória |
|---|---|---|
| QG-INTAKE | sponsor, objetivo, tipo, dados e restrições identificados | brief e classificação |
| QG-DISCOVERY | problema, fontes, hipóteses e decisão documentados | síntese validada |
| QG-ANALYSIS | requisitos, regras, escopo e aceite rastreáveis | catálogo e aprovação |
| QG-ARCH | atributos, alternativas, fronteiras e falhas tratados | arquitetura + ADRs |
| QG-PLAN | entregas, dependências, riscos e responsáveis definidos | backlog e roadmap |
| QG-DESIGN | jornadas, estados, conteúdo e acessibilidade revisados | protótipo/especificação |
| QG-IMPLEMENT | critérios vinculados, checks e revisão concluídos | mudança e relatórios |
| QG-TEST | riscos e jornadas críticas cobertos, defeitos classificados | plano e relatório |
| QG-SECURITY | threat model, controles e achados tratados | revisão de segurança |
| QG-DEPLOY | rollback, observação, runbook e go/no-go prontos | plano e aprovação |
| QG-DOC | público, operação e mudanças documentados | documentação revisada |
| QG-HANDOVER | ativos, acessos, pendências e ownership transferidos | aceite do receptor |
| QG-CLOSE | aceite, retenção, métricas e retrospectiva concluídos | relatório de encerramento |

Falha bloqueia a transição ou gera exceção formal com dono, validade e plano. Catálogo: `registry/quality-gates.yaml`.
'@
"core/GOVERNANCE.md" = @'
# Governança

**Dono:** Executive; **status:** ativo

Papéis decidem apenas dentro da autoridade de `core/ORGANIZATION.md`. Mudanças de Core, contratos, Registry ou gates exigem proposta, impacto, revisores dos domínios afetados, aprovação do dono e versão. Workflows exigem Orchestrator, Delivery e Quality; standards exigem dono do domínio; criação/remoção de agentes exige Orchestrator, departamento e verificação de contratos.

Versionamento usa SemVer. Exceção informa regra, motivo, risco, aprovador, escopo, validade e plano de remoção. Auditoria verifica versões, aprovações, eventos, caminhos e segregação de funções. Remoções são deprecações antes de exclusão e nunca quebram projetos ativos.
'@
"core/ESCALATION.md" = @'
# Escalonamento

Interrompa diante de falta de autorização, entrada crítica ausente, contradição material, conflito de autoridade, risco alto, incidente, decisão irreversível ou gate sem evidência. Registre fato, impacto, ações seguras já tentadas, alternativas, recomendação, autoridade necessária e prazo. Segurança/privacidade pode bloquear; Sponsor resolve impacto contratual; Product resolve valor; Tech Lead resolve arquitetura; Quality decide suficiência de evidência.
'@
"core/CHANGE-MANAGEMENT.md" = @'
# Gestão de Mudanças

Toda mudança material registra origem, motivação, escopo, artefatos afetados, impacto em prazo/custo/risco, alternativas, compatibilidade, plano de migração/rollback, aprovações e comunicação. Emergências podem usar rito acelerado, com regularização e retrospectiva. Mudanças de padrão, contrato ou workflow atualizam versão e Registry; projetos ativos adotam explicitamente ou permanecem na versão fixada.
'@
"core/SECURITY.md" = @'
# Segurança e Privacidade da Plataforma

Aplicam-se minimização, need-to-know, privilégio mínimo, segregação de clientes, classificação, retenção e auditoria. Segredos e dados reais de clientes não entram neste repositório, prompts, memória global ou logs. Ferramentas de IA exigem autorização e classificação compatível. Incidentes seguem `playbooks/incident-response.md`. Threat model, identidade, autorização, supply chain, backup e recuperação serão requisitos do Runtime futuro, não capacidades presumidas desta versão documental.
'@
}
foreach ($item in $core.GetEnumerator()) { Write-Doc $item.Key $item.Value }

$roles = @(
@("executive","Executive","direção, estratégia e risco empresarial"),
@("orchestrator","Orchestrator","coordenação do sistema e gates"),
@("business-analysis","Business Analysis","descoberta e requisitos"),
@("architecture","Architecture","arquitetura e decisões técnicas"),
@("project-management","Project Management","planejamento e entrega"),
@("product-design","Product Design","experiência, pesquisa e interface"),
@("database-engineering","Database Engineering","dados, integridade e migração"),
@("backend-engineering","Backend Engineering","serviços e integrações"),
@("frontend-engineering","Frontend Engineering","experiências web"),
@("mobile-engineering","Mobile Engineering","experiências móveis"),
@("ai-engineering","AI Engineering","sistemas com IA e avaliação"),
@("quality-assurance","Quality Assurance","estratégia e evidência de qualidade"),
@("security-engineering","Security Engineering","riscos e controles"),
@("devops-engineering","DevOps Engineering","entrega e confiabilidade"),
@("documentation-engineering","Documentation Engineering","informação utilizável"),
@("support-maintenance","Support & Maintenance","continuidade e evolução")
)
foreach ($r in $roles) {
Write-Doc "roles/$($r[0]).md" @"
# Papel: $($r[1])

**Dono:** departamento correspondente; **status:** ativo; **versão:** 0.1.0

## Missão

Garantir $($r[2]) com decisões rastreáveis e evidência verificável.

## Responsabilidades e autoridade

Define práticas e recomenda decisões do domínio; aprova entregas quando indicado por `core/ORGANIZATION.md`; mantém artefatos, riscos e qualidade sob sua responsabilidade.

## Limites

Não substitui Product Manager, Sponsor ou especialistas de outros domínios; não publica, gasta, acessa dados restritos nem aceita risco material sem autoridade humana.

## Entradas e saídas

Recebe brief, contexto, artefatos anteriores, restrições e standards. Produz análise, decisão/recomendação, artefatos do domínio, evidências de gate e handoff.

## Relacionamentos

Coordena com Orchestrator e Delivery; consulta Product, Architecture, Quality, Security e Operations conforme impacto.

## Indicadores de qualidade

Rastreabilidade das decisões; ausência de gate sem evidência; achados resolvidos ou aceitos por autoridade; handoffs aceitos sem lacuna crítica.

## Aprovação humana obrigatória

Decisão irreversível, mudança material de escopo/custo/prazo, produção, dados sensíveis, exceção a standard ou risco alto.
"@
}

$departments = @(
@("executive","Executive","estratégia e sustentabilidade"),
@("business","Business","valor, problema e requisitos"),
@("architecture","Architecture","coerência técnica"),
@("product-design","Product Design","experiência e acessibilidade"),
@("engineering","Engineering","implementação sustentável"),
@("data","Data","qualidade e governança de dados"),
@("quality","Quality","evidência de qualidade"),
@("security","Security","proteção e risco"),
@("operations","Operations","entrega e confiabilidade"),
@("documentation","Documentation","clareza e transferência")
)
foreach ($d in $departments) {
Write-Doc "departments/$($d[0]).md" @"
# Departamento: $($d[1])

## Missão
Responder por $($d[2]) na ASEP.

## Responsabilidades
Manter competências, standards, agentes, capacidade, revisão e evidências do domínio.

## Limites e autoridade
Decide dentro do domínio e escala conflitos interdepartamentais. Não altera contrato, escopo ou risco material unilateralmente.

## Entradas e saídas
Recebe demandas, contexto, dependências e achados; entrega recomendações, artefatos revisados, decisões e handoffs.

## Relacionamentos
Opera por contratos com os demais departamentos e pelo Orchestrator.

## Indicadores de qualidade
Tempo de resposta a bloqueios, reincidência de achados, aceitação de handoffs e atualização dos padrões.

## Aprovação humana
Obrigatória para mudança de política, produção, gasto, dados restritos, exceções e risco alto.
"@
}

$agents = @(
@("orchestrator","Orchestrator","Operations","orquestrar demandas, workflows, gates e encerramento","project-record, workflow-run, consolidated-handover","não cria requisitos, não decide arquitetura sozinho, não implementa código e não autoaprova conflito"),
@("business-analyst","Business Analyst","Business","transformar necessidades confirmadas em requisitos rastreáveis","requirements, business-rules, scope, assumptions","não inventa requisitos nem escolhe solução técnica"),
@("software-architect","Software Architect","Architecture","definir arquitetura justificada por atributos de qualidade","architecture-document, adr, threat-model-input","não cria prioridade de produto nem implementa todo o sistema"),
@("project-manager","Project Manager","Operations","planejar e coordenar entrega, dependências e riscos","roadmap, backlog, risk-register, status-report","não promete prazo sem evidência nem redefine escopo"),
@("ux-ui-designer","UX/UI Designer","Product Design","projetar jornadas acessíveis baseadas em evidência","user-flows, design-specification, accessibility-review","não inventa pesquisa nem decide regra de negócio"),
@("database-engineer","Database Engineer","Data","projetar dados íntegros, seguros e recuperáveis","data-model, database-design, migration-plan","não escolhe produto nem ignora ownership de dados"),
@("backend-engineer","Backend Engineer","Engineering","implementar serviços e integrações conforme contratos","backend-change, api-implementation, test-evidence","não altera contrato de API unilateralmente"),
@("frontend-engineer","Frontend Engineer","Engineering","implementar experiências web acessíveis e observáveis","frontend-change, ui-test-evidence","não altera design ou regra sem validação"),
@("mobile-engineer","Mobile Engineer","Engineering","implementar experiências móveis confiáveis","mobile-change, mobile-test-evidence","não ignora políticas de plataforma ou acessibilidade"),
@("ai-engineer","AI Engineer","Engineering","projetar componentes de IA avaliáveis e seguros","ai-design, evaluation-plan, model-card","não apresenta saída probabilística como fato"),
@("qa-engineer","QA Engineer","Quality","definir e executar validação orientada a risco","test-plan, test-report, release-recommendation","não aprova risco fora de sua autoridade"),
@("security-engineer","Security Engineer","Security","identificar ameaças e verificar controles","threat-model, security-review, findings","não aceita risco material pelo negócio"),
@("devops-engineer","DevOps Engineer","Operations","preparar entrega, observabilidade e recuperação","deployment-plan, runbook, operational-evidence","não publica sem aprovação e rollback"),
@("documentation-engineer","Documentation Engineer","Documentation","produzir informação correta, localizável e transferível","user-guide, technical-documentation, handover","não inventa comportamento do produto"),
@("support-engineer","Support Engineer","Operations","sustentar serviço e transformar sinais em melhoria","incident-record, support-report, maintenance-plan","não modifica produção fora do change process")
)

$legacyBA = ""
$baPath = Join-Path $Root "agents/business-analyst.md"
if (Test-Path $baPath) { $legacyBA = [System.IO.File]::ReadAllText($baPath) }

foreach ($a in $agents) {
$id=$a[0]; $name=$a[1]; $dept=$a[2]; $mission=$a[3]; $outputs=$a[4]; $cannot=$a[5]
$preserved = ""
if ($id -eq "business-analyst" -and $legacyBA) {
    $preserved = "`n### Referência especializada preservada`n`nO manual anterior continha roteiros detalhados de discovery, requisitos, regras, MVP e critérios de aceite. Seu conteúdo útil permanece como fonte complementar em ``knowledge/business/requirements.md`` e nos playbooks de discovery e requirements; nenhuma exigência confirmada foi descartada."
}
Write-Doc "agents/$id.md" @"
# Agente: $name

**Versão:** 0.1.0 | **Status:** ativo | **Dono:** $dept

## 1. Identidade
Especialista ASEP de $dept, orientado por evidências.
## 2. Cargo
$name.
## 3. Departamento
$dept.
## 4. Missão
$mission.
## 5. Objetivo
Produzir resultado verificável do domínio sem extrapolar autoridade.
## 6. Papel
Executar tarefas contratadas e colaborar por handoff.
## 7. Autoridade
Recomendar e decidir apenas itens reversíveis do domínio; decisões materiais seguem governança.
## 8. Responsabilidades
Validar entradas; separar fatos e hipóteses; executar o processo; registrar decisões; revisar; produzir evidências.
## 9. O que não faz
$cannot; não inventa requisitos, fatos, testes ou aprovações.
## 10. Conhecimentos necessários
Práticas do domínio, lifecycle ASEP, gestão de risco, rastreabilidade, segurança, privacidade, acessibilidade e comunicação.
$preserved
## 11. Fontes obrigatórias de consulta
`AGENTS.md`, `core/SYSTEM.md`, `contracts/$id.yaml`, projeto, workflow, standards e knowledge aplicáveis.
## 12. Entradas
Objetivo, contexto autorizado, artefatos predecessores, restrições, critérios de aceite e gate.
## 13. Validação das entradas
Verificar existência, origem, versão, autorização, consistência, completude crítica e compatibilidade contratual.
## 14. Processo de execução
Load → Validate → Load Contract → Load Knowledge → Load Standards → Load Context → Execute → Self Review → Quality Validation → Generate Artifacts → Handoff → Finish.
## 15. Entregáveis
$outputs.
## 16. Estrutura dos artefatos
Metadados, objetivo, fontes, conteúdo, fatos/hipóteses, decisões, evidências, riscos, pendências e próximos passos.
## 17. Critérios de qualidade
Correção, completude do escopo, rastreabilidade, verificabilidade, clareza, segurança e compatibilidade com a próxima entrada.
## 18. Checklist de autoavaliação
- [ ] Entradas e autoridade validadas.
- [ ] Fatos, hipóteses e decisões separados.
- [ ] Standards e gates atendidos com evidência.
- [ ] Trabalho de outros domínios não foi usurpado.
- [ ] Handoff e pendências têm dono e gatilho.
## 19. Comunicação
Usar `core/COMMUNICATION.md`; comunicar bloqueio cedo e registrar decisão fora de chats.
## 20. Passagem para o próximo agente
Entregar artefatos versionados, validações, riscos, lacunas e recomendação; receptor confirma compatibilidade.
## 21. Quando interromper
Entrada crítica ausente/contraditória, autorização insuficiente ou evidência incapaz de sustentar a conclusão.
## 22. Quando escalar
Risco alto, conflito de autoridade, incidente, mudança material ou gate bloqueado.
## 23. Quando pedir decisão humana
Publicação, gasto, dados restritos, aceite material, exceção, decisão irreversível ou risco residual alto.
## 24. Erros proibidos
Inventar; ocultar incerteza; aprovar sem evidência; expor segredo; apagar rastreabilidade; invadir domínio.
## 25. Critérios de conclusão
Saídas obrigatórias existentes, gate avaliado, decisão registrada, handoff aceito e nenhuma pendência crítica sem dono.
## 26. Exemplo de execução
Recebe tarefa com artefatos versionados; valida fontes; registra hipótese pendente; produz $outputs; anexa evidência; encaminha ao agente previsto ou bloqueia com decisão necessária.
## 27. Prompt operacional
> Você é $name. Sua missão é $mission. Siga AGENTS.md e seu contrato. Não invente requisitos ou evidências. Valide entradas, declare hipóteses, permaneça no domínio, faça self-review, produza evidência para gates e finalize com handoff rastreável. Interrompa e escale quando faltar dado crítico, autoridade ou segurança.
"@
}

$nextMap = @{
"orchestrator"=@("business-analyst","project-manager"); "business-analyst"=@("software-architect","ux-ui-designer");
"software-architect"=@("project-manager","database-engineer","security-engineer"); "project-manager"=@("ux-ui-designer","backend-engineer");
"ux-ui-designer"=@("frontend-engineer","mobile-engineer"); "database-engineer"=@("backend-engineer");
"backend-engineer"=@("qa-engineer"); "frontend-engineer"=@("qa-engineer"); "mobile-engineer"=@("qa-engineer");
"ai-engineer"=@("qa-engineer","security-engineer"); "qa-engineer"=@("security-engineer","devops-engineer");
"security-engineer"=@("devops-engineer"); "devops-engineer"=@("documentation-engineer");
"documentation-engineer"=@("support-engineer"); "support-engineer"=@()
}
$outputMap = @{}
foreach($a in $agents){$outputMap[$a[0]]=$a[4].Split(", ")}
foreach ($a in $agents) {
$id=$a[0]; $name=$a[1]; $dept=$a[2]; $mission=$a[3]; $cannot=$a[5]
$required = if($id -eq "orchestrator"){@("project-brief")} elseif($id -eq "business-analyst"){@("project-brief")} else {@("project-context","approved-predecessor-artifacts")}
$receives = @($required + @("constraints","decisions","risk-register")) | Select-Object -Unique
$produces = $outputMap[$id]
$next = $nextMap[$id]
$yamlList = { param($items,$indent=2) (($items | ForEach-Object { (" " * $indent) + "- " + $_ }) -join "`n") }
Write-Doc "contracts/$id.yaml" @"
id: $id
name: "$name"
version: 0.1.0
status: active
department: "$dept"
role: "$id"
reports_to: orchestrator
mission: "$mission"
capabilities:
$(& $yamlList @("analyze-context","validate-inputs","produce-evidence","self-review","handoff"))
receives:
$(& $yamlList $receives)
required_inputs:
$(& $yamlList $required)
optional_inputs:
$(& $yamlList @("constraints","decisions","risk-register"))
produces:
$(& $yamlList $produces)
required_outputs:
$(& $yamlList $produces)
consults:
$(& $yamlList @("../AGENTS.md","../core/SYSTEM.md","../core/QUALITY.md","../agents/$id.md"))
quality_gates:
$(& $yamlList @(if($id -eq "orchestrator"){"QG-INTAKE";"QG-CLOSE"} elseif($id -eq "business-analyst"){"QG-ANALYSIS"} elseif($id -eq "software-architect"){"QG-ARCH"} elseif($id -eq "project-manager"){"QG-PLAN"} elseif($id -eq "ux-ui-designer"){"QG-DESIGN"} elseif($id -in @("qa-engineer")){"QG-TEST"} elseif($id -eq "security-engineer"){"QG-SECURITY"} elseif($id -eq "devops-engineer"){"QG-DEPLOY"} elseif($id -eq "documentation-engineer"){"QG-DOC"} elseif($id -eq "support-engineer"){"QG-CLOSE"} else {"QG-IMPLEMENT"}))
approval_rules:
  - "gate owner approves evidence; agent cannot self-approve conflicts"
next_agents:
$(& $yamlList $next)
cannot:
$(& $yamlList @($cannot,"invent requirements or evidence","exceed domain authority"))
human_approval_required:
$(& $yamlList @("production","material scope/cost/time change","high residual risk","sensitive data access","irreversible decision"))
escalation_conditions:
$(& $yamlList @("missing critical input","authority conflict","high risk","failed quality gate"))
success_criteria:
$(& $yamlList @("required outputs exist","evidence accepted","handoff compatible","open critical items have owner"))
failure_conditions:
$(& $yamlList @("fabricated evidence","unauthorized action","missing required output","unresolved blocking gate"))
"@
}

Write-Doc "roles/README.md" "# Papéis`n`nPapéis definem autoridade organizacional. Agentes implementam especialidades e contratos definem interfaces. Catálogo: ``registry/roles.yaml``."
Write-Doc "departments/README.md" "# Departamentos`n`nDepartamentos mantêm competências e standards. Catálogo: ``registry/departments.yaml``."
Write-Doc "contracts/README.md" "# Contratos`n`nInterfaces YAML versionadas entre agentes. Mudanças seguem ``core/GOVERNANCE.md``."

Write-Doc "registry/agents.yaml" ("version: 0.1.0`nagents:`n" + (($agents | ForEach-Object {
"  - id: $($_[0])`n    name: `"$($_[1])`"`n    version: 0.1.0`n    status: active`n    capabilities: [validate-inputs, produce-evidence, self-review, handoff]`n    contract: ../contracts/$($_[0]).yaml`n    manual: ../agents/$($_[0]).md`n    department: $($_[2])`n    dependencies: [core-system, quality-gates]`n    applicable_project_types: [software, saas, web, mobile, ai, automation, maintenance]"
}) -join "`n"))
Write-Doc "registry/roles.yaml" ("version: 0.1.0`nroles:`n" + (($roles | ForEach-Object {"  - id: $($_[0])`n    name: `"$($_[1])`"`n    path: ../roles/$($_[0]).md"}) -join "`n"))
Write-Doc "registry/departments.yaml" ("version: 0.1.0`ndepartments:`n" + (($departments | ForEach-Object {"  - id: $($_[0])`n    name: `"$($_[1])`"`n    path: ../departments/$($_[0]).md"}) -join "`n"))
Write-Doc "registry/contracts.yaml" ("version: 0.1.0`ncontracts:`n" + (($agents | ForEach-Object {"  - id: $($_[0])`n    version: 0.1.0`n    path: ../contracts/$($_[0]).yaml"}) -join "`n"))

Write-Doc "registry/quality-gates.yaml" @'
version: 0.1.0
quality_gates:
  - { id: QG-INTAKE, owner: orchestrator, definition: ../core/QUALITY.md }
  - { id: QG-DISCOVERY, owner: business-analyst, definition: ../core/QUALITY.md }
  - { id: QG-ANALYSIS, owner: business-analyst, definition: ../core/QUALITY.md }
  - { id: QG-ARCH, owner: software-architect, definition: ../core/QUALITY.md }
  - { id: QG-PLAN, owner: project-manager, definition: ../core/QUALITY.md }
  - { id: QG-DESIGN, owner: ux-ui-designer, definition: ../core/QUALITY.md }
  - { id: QG-IMPLEMENT, owner: qa-engineer, definition: ../core/QUALITY.md }
  - { id: QG-TEST, owner: qa-engineer, definition: ../core/QUALITY.md }
  - { id: QG-SECURITY, owner: security-engineer, definition: ../core/QUALITY.md }
  - { id: QG-DEPLOY, owner: devops-engineer, definition: ../core/QUALITY.md }
  - { id: QG-DOC, owner: documentation-engineer, definition: ../core/QUALITY.md }
  - { id: QG-HANDOVER, owner: orchestrator, definition: ../core/QUALITY.md }
  - { id: QG-CLOSE, owner: orchestrator, definition: ../core/QUALITY.md }
'@

$workflowDocs = @("project-intake","new-client","new-project","discovery","business-analysis","architecture","planning","product-design","implementation","code-review","testing","security-review","deployment","documentation","handover","maintenance","change-request","incident-response","project-closure","retrospective")
$workflowOwner = @{
"project-intake"="orchestrator";"new-client"="orchestrator";"new-project"="orchestrator";"discovery"="business-analyst";"business-analysis"="business-analyst";"architecture"="software-architect";"planning"="project-manager";"product-design"="ux-ui-designer";"implementation"="backend-engineer";"code-review"="qa-engineer";"testing"="qa-engineer";"security-review"="security-engineer";"deployment"="devops-engineer";"documentation"="documentation-engineer";"handover"="orchestrator";"maintenance"="support-engineer";"change-request"="project-manager";"incident-response"="support-engineer";"project-closure"="orchestrator";"retrospective"="project-manager"
}
foreach($w in $workflowDocs){
Write-Doc "workflows/$w.md" @"
# Workflow: $w

**Dono:** $($workflowOwner[$w]) | **Versão:** 0.1.0 | **Status:** ativo

## Entrada e validação
Receber registro do projeto, objetivo, artefatos predecessores, decisões e restrições. Validar contrato, autorização, versão, dependências e dados críticos.

## Execução
1. Registrar `stage.started`.
2. Carregar agente, contrato, knowledge, standards e playbook aplicáveis.
3. Executar o menor incremento verificável e registrar decisões.
4. Fazer self-review e revisão independente quando exigida.
5. Avaliar gate com evidências; retornar para correção se falhar.
6. Produzir handoff ou registrar bloqueio/cancelamento.

## Saída, gate e falhas
Saída é artefato versionado, evidência, riscos, decisões e próxima ação. Gate aplicável vem de `registry/quality-gates.yaml`. Falha preserva estado, causa e opção de retomada. Aprovação humana é solicitada para impacto material ou condição do contrato.
"@
}

$workflowTypes = @("software","saas","web","mobile","ai","automation","maintenance")
foreach($type in $workflowTypes){
$implAgents = if($type -eq "mobile"){"[mobile-engineer, backend-engineer]"} elseif($type -eq "ai"){"[ai-engineer, backend-engineer]"} elseif($type -eq "web"){"[frontend-engineer, backend-engineer]"} elseif($type -eq "maintenance"){"[support-engineer]"} else {"[backend-engineer, frontend-engineer]"}
Write-Doc "workflows/$type-project.yaml" @"
id: $type-project
name: "$type project workflow"
version: 0.1.0
description: "Lifecycle declarativo para projeto $type; etapas condicionais são decididas no intake."
applicable_project_types: [$type]
required_context: [project-brief, sponsor, data-classification, success-criteria]
stages:
  - { id: intake, mode: sequential, workflow: project-intake }
  - { id: discovery, mode: sequential, workflow: discovery }
  - { id: analysis, mode: sequential, workflow: business-analysis }
  - { id: architecture, mode: sequential, workflow: architecture }
  - { id: planning_design, mode: parallel, workflows: [planning, product-design] }
  - { id: implementation, mode: sequential, workflow: implementation }
  - { id: assurance, mode: parallel, workflows: [testing, security-review, documentation] }
  - { id: deployment, mode: conditional, workflow: deployment }
  - { id: handover, mode: sequential, workflow: handover }
  - { id: retrospective, mode: sequential, workflow: retrospective }
stage_dependencies:
  discovery: [intake]
  analysis: [discovery]
  architecture: [analysis]
  planning_design: [architecture]
  implementation: [planning_design]
  assurance: [implementation]
  deployment: [assurance]
  handover: [deployment]
  retrospective: [handover]
assigned_agents:
  intake: [orchestrator]
  discovery: [business-analyst]
  analysis: [business-analyst]
  architecture: [software-architect, security-engineer]
  planning_design: [project-manager, ux-ui-designer]
  implementation: $implAgents
  assurance: [qa-engineer, security-engineer, documentation-engineer]
  deployment: [devops-engineer]
  handover: [orchestrator, support-engineer]
  retrospective: [project-manager]
conditions:
  - "design may be not_applicable only with recorded justification"
  - "deployment runs only for an approved release target"
  - "failed gates return to the producing stage"
  - "blocked stages require owner and resume trigger"
quality_gates: [QG-INTAKE, QG-DISCOVERY, QG-ANALYSIS, QG-ARCH, QG-PLAN, QG-DESIGN, QG-IMPLEMENT, QG-TEST, QG-SECURITY, QG-DEPLOY, QG-DOC, QG-HANDOVER, QG-CLOSE]
human_approvals: [scope-baseline, architecture-high-risk, production-go-no-go, residual-risk, project-closure]
artifacts: [project-brief, requirements, architecture-document, roadmap, backlog, test-report, security-review, deployment-plan, handover, retrospective]
failure_handling:
  retry: "only for transient and idempotent operations"
  correction: "return with findings and preserved history"
  blocking: "record cause, owner and resume trigger"
  cancellation: "preserve audit, artifacts and retention duties"
  resumption: "revalidate context, versions, approvals and dependencies"
completion_criteria: [all-required-stages-completed, all-gates-decided, human-approvals-recorded, handover-accepted, no-unowned-critical-pendency]
"@
}

Write-Doc "registry/workflows.yaml" ("version: 0.1.0`nworkflows:`n" + (($workflowTypes | ForEach-Object {"  - id: $_-project`n    name: `"$_ project workflow`"`n    version: 0.1.0`n    purpose: `"govern project type $_`"`n    project_types: [$_]`n    stages: [intake, discovery, analysis, architecture, planning_design, implementation, assurance, deployment, handover, retrospective]`n    agents: [orchestrator, business-analyst, software-architect, project-manager, ux-ui-designer, qa-engineer, security-engineer, devops-engineer, documentation-engineer, support-engineer]`n    conditions: [gates, approvals, correction, blocking, cancellation, resumption]`n    gates: [QG-INTAKE, QG-ANALYSIS, QG-ARCH, QG-PLAN, QG-IMPLEMENT, QG-TEST, QG-SECURITY, QG-DEPLOY, QG-HANDOVER, QG-CLOSE]`n    approvals: [scope-baseline, production-go-no-go, project-closure]`n    path: ../workflows/$_-project.yaml"}) -join "`n"))

$playbooks = @("new-client","new-project","discovery","requirements","architecture","planning","ux-design","database-design","api-design","implementation","code-review","testing","security-review","deployment","maintenance","incident-response","change-management","project-recovery","retrospective")
foreach($p in $playbooks){
Write-Doc "playbooks/$p.md" @"
# Playbook: $p

## Objetivo
Conduzir $p com evidência, limites de autoridade e saída transferível.
## Quando usar
Quando o workflow ou um achado exigir esta capacidade.
## Pré-condições
Projeto identificado, objetivo, owner, contexto autorizado e contrato dos participantes.
## Participantes
Orchestrator, dono do domínio e revisores indicados pelo risco.
## Entradas
Artefatos predecessores, decisões, restrições, riscos e critérios.
## Procedimento
Validar → analisar fatos/hipóteses → comparar opções → executar incremento → self-review → gate → handoff.
## Decisões
Registrar alternativas, impacto, recomendação, autoridade e resultado.
## Checklist
- [ ] Entradas e autorização válidas.
- [ ] Standards e riscos aplicáveis tratados.
- [ ] Evidências anexadas e artefatos versionados.
- [ ] Pendências, exceções e handoff registrados.
## Artefatos
Artefato do domínio, evidências de revisão, registro de decisões e handoff.
## Quality gates
Usar o gate da fase em `registry/quality-gates.yaml`; ausência de evidência bloqueia.
## Riscos
Ambiguidade, dado não autorizado, conflito de responsabilidade e decisão implícita.
## Exceções
Registrar justificativa, aprovador, validade e plano de correção.
## Critérios de encerramento
Saída aceita pelo contrato seguinte e nenhuma pendência crítica sem dono.
"@
}

$knowledgeAreas = @{
"business"=@("requirements","stakeholders","personas","user-stories","use-cases","business-rules","mvp","prioritization");
"architecture"=@("principles","architecture-selection","modular-monolith","microservices","clean-architecture","ddd","api-design","event-driven","scalability","resilience");
"project-management"=@("estimation","backlog","risk-management","dependencies","delivery-planning");
"testing"=@("test-strategy","test-pyramid","acceptance-testing","regression","automation");
"security"=@("secure-development","threat-modeling","authentication","authorization","secrets","privacy")
}
$knowledgeFocus = @{
"requirements"="requisitos claros, singulares, testáveis e rastreáveis à fonte";
"stakeholders"="autoridade, interesse, impacto e participação de cada grupo";
"personas"="perfis baseados em evidência, sem estereótipos";
"user-stories"="necessidade e valor, complementados por critérios verificáveis";
"use-cases"="atores, precondições, fluxo principal, alternativas e pós-condições";
"business-rules"="regras com fonte, vigência, exceções e precedência";
"mvp"="menor incremento coerente capaz de testar valor ou operação";
"prioritization"="valor, risco, dependência e custo de atraso";
"principles"="fronteiras, coesão, acoplamento, evolução e operabilidade";
"architecture-selection"="alternativas guiadas por atributos de qualidade e restrições";
"modular-monolith"="módulos fortes com implantação unificada e caminho de evolução";
"microservices"="serviços autônomos somente quando autonomia compensa custo distribuído";
"clean-architecture"="dependências orientadas ao domínio sem dogma estrutural";
"ddd"="linguagem ubíqua, bounded contexts e modelos coerentes";
"api-design"="contratos compatíveis, seguros, idempotentes e observáveis";
"event-driven"="eventos com semântica, ownership, entrega e recuperação explícitos";
"scalability"="capacidade baseada em carga, gargalos, metas e custo";
"resilience"="timeouts, retries, idempotência, degradação e recuperação";
"estimation"="faixas, incerteza, premissas e atualização por evidência";
"backlog"="itens orientados a resultado, refinados e rastreáveis";
"risk-management"="evento, probabilidade, impacto, resposta, dono e gatilho";
"dependencies"="dependências com dono, data, impacto e alternativa";
"delivery-planning"="incrementos, capacidade, caminho crítico e critérios de replanejamento";
"test-strategy"="cobertura orientada a riscos, requisitos e ambientes";
"test-pyramid"="feedback rápido na base e poucos testes ponta a ponta essenciais";
"acceptance-testing"="evidência observável de critérios de negócio";
"regression"="seleção por impacto e histórico, com baseline confiável";
"automation"="automação estável, determinística, mantida e útil ao feedback";
"secure-development"="ameaças e controles ao longo de todo lifecycle";
"threat-modeling"="ativos, atores, trust boundaries, abuso, mitigação e risco residual";
"authentication"="identidade, sessão, recuperação e resistência a abuso";
"authorization"="deny-by-default, servidor, menor privilégio e teste de isolamento";
"secrets"="cofre, rotação, escopo, auditoria e resposta a exposição";
"privacy"="finalidade, minimização, base autorizada, retenção e direitos"
}
foreach($area in $knowledgeAreas.Keys){
foreach($topic in $knowledgeAreas[$area]){
$focus=$knowledgeFocus[$topic]
Write-Doc "knowledge/$area/$topic.md" @"
# $topic

## Objetivo
Orientar decisões sobre $focus.
## Conceitos
O tema deve ser descrito com fonte, contexto, estado e relação com requisitos ou riscos.
## Princípios
Evidência antes de suposição; simplicidade proporcional; segurança e operação por design; decisão reversível quando possível.
## Boas práticas
Definir ownership; tornar critérios observáveis; comparar alternativas; registrar exceções e validar com participantes afetados.
## Critérios de decisão
Resultado, risco, restrições, custo total, reversibilidade, capacidade e evidência disponível.
## Erros comuns
Copiar solução sem contexto; usar termos vagos; omitir exceções; transformar hipótese em fato; criar artefato sem dono.
## Checklist
- [ ] Objetivo e fonte claros.
- [ ] Alternativas, riscos e exceções considerados.
- [ ] Decisão ligada a requisito, workflow e evidência.
## Relação com agentes
O especialista do domínio aplica; Business Analyst preserva origem; Architect avalia impacto técnico; QA transforma risco em validação.
## Relação com workflows
Consultado nas fases de discovery, definição, execução e review conforme aplicabilidade.
## Referências internas
`core/QUALITY.md`, `standards/`, `playbooks/` e contrato do agente responsável.
"@
}
}

$extraAreas = @("backend","frontend","database","mobile","ux","devops","ai","documentation","operations")
foreach($area in $extraAreas){
Add-Doc "knowledge/$area/README.md" @"
# Knowledge: $area

## Objetivo
Reunir conhecimento fundamental e validado de $area sem impor tecnologia.
## Conceitos e princípios
Decisões consideram requisitos, risco, operabilidade, segurança, custo e capacidade.
## Boas práticas e critérios
Prefira contratos claros, mudanças pequenas, evidência automatizada e alternativas registradas.
## Erros comuns
Escolha por preferência, ausência de ownership e documentação sem contexto.
## Checklist
- [ ] Fontes e aplicabilidade claras.
- [ ] Relações com agentes e workflows registradas.
## Relações
Consulte o agente e o standard de mesmo domínio, além de `core/QUALITY.md`.
"@
}

$standards = @("documentation","naming","versioning","repository-structure","requirements","architecture","adr","api","database","backend","frontend","mobile","ai","testing","security","devops","observability","code-review","git")
foreach($s in $standards){
Write-Doc "standards/$s.md" @"
# Standard: $s

**Dono:** responsável do domínio | **Versão:** 0.1.0 | **Status:** ativo

## Obrigatório
- Identificar objetivo, dono, versão, fontes, risco e critérios verificáveis.
- Preservar rastreabilidade, segurança, privacidade e compatibilidade.
- Registrar decisão material, exceção e evidência de validação.

## Recomendado
- Preferir soluções simples, reversíveis, automatizáveis e conhecidas pela equipe.
- Fazer mudanças pequenas e revisão independente proporcional ao risco.

## Dependente do contexto
Tecnologia, profundidade, técnica e nível de automação são escolhidos por requisitos, risco, capacidade e custo total.

## Exceção permitida
Somente com regra afetada, justificativa, impacto, aprovador autorizado, escopo, validade e plano de remoção.

## Evidência
Artefato versionado, checklist preenchido, resultado de validação e links para requisitos/decisões.
"@
}

$templates = @(
@("business","project-brief"),@("business","executive-summary"),@("business","stakeholder-map"),@("business","personas"),@("business","requirements"),@("business","business-rules"),@("business","user-stories"),@("business","scope"),@("planning","risks"),@("planning","assumptions"),@("architecture","architecture-document"),@("architecture","adr"),@("architecture","api-contract"),@("architecture","database-design"),@("planning","technical-roadmap"),@("planning","backlog"),@("testing","test-plan"),@("testing","test-report"),@("security","security-review"),@("deployment","deployment-plan"),@("operations","runbook"),@("documentation","user-guide"),@("documentation","handover"),@("operations","retrospective"),@("operations","lessons-learned"),@("planning","change-request"),@("operations","incident-report")
)
foreach($t in $templates){
Write-Doc "templates/$($t[0])/$($t[1]).md" @"
# Template: $($t[1])

> Instrução: copie para o projeto, substitua os campos entre colchetes e remova orientações. `TODO` exige dono e data.

**ID:** [identificador] | **Versão:** [semver] | **Status:** [draft/review/approved]  
**Dono:** [papel] | **Data:** [YYYY-MM-DD] | **Fontes:** [links]

## Objetivo
[Resultado ou decisão que este artefato suporta. Exemplo mínimo: “informar o gate QG-X”.]
## Contexto e escopo
[Fatos confirmados, limites e público.]
## Entradas e validações
[Fonte, versão, autorização e resultado da validação.]
## Conteúdo
[Informação específica; use IDs rastreáveis e critérios observáveis.]
## Fatos, hipóteses e perguntas
| Tipo | Declaração | Fonte/dono | Gatilho |
|---|---|---|---|
## Decisões e alternativas
[ID, opções, impacto, recomendação, autoridade e status.]
## Riscos e exceções
[Evento, impacto, resposta, dono e validade.]
## Evidências e quality gate
[Critério → evidência real → resultado.]
## Pendências e handoff
[Próxima ação, responsável e prazo ou gatilho.]
"@
}

foreach($dir in @("business","architecture","planning","design","engineering","testing","security","deployment","documentation","operations")){
Add-Doc "templates/$dir/README.md" "# Templates: $dir`n`nModelos de $dir. Copie para o projeto; não edite o template para registrar dados de cliente."
}

Write-Doc "registry/knowledge.yaml" ("version: 0.1.0`nknowledge:`n" + (($knowledgeAreas.Keys | Sort-Object | ForEach-Object {$area=$_; $knowledgeAreas[$area] | ForEach-Object {"  - id: $area-$_`n    path: ../knowledge/$area/$_.md"}}) -join "`n"))
Write-Doc "registry/playbooks.yaml" ("version: 0.1.0`nplaybooks:`n" + (($playbooks | ForEach-Object {"  - id: $_`n    path: ../playbooks/$_.md"}) -join "`n"))
Write-Doc "registry/templates.yaml" ("version: 0.1.0`ntemplates:`n" + (($templates | ForEach-Object {"  - id: $($_[1])`n    path: ../templates/$($_[0])/$($_[1]).md"}) -join "`n"))
Write-Doc "registry/standards.yaml" ("version: 0.1.0`nstandards:`n" + (($standards | ForEach-Object {"  - id: $_`n    path: ../standards/$_.md"}) -join "`n"))

Write-Doc "artifacts/README.md" @'
# Artefatos Globais

Artefatos específicos pertencem a `projects/<id>/`. Esta pasta contém apenas ativos reutilizáveis globais, sanitizados, aprovados e registrados em `memory/reusable-assets/`. Não recebe cópias de entregáveis de projetos nem dados de clientes. O aprovador é o dono do domínio e, quando houver risco de confidencialidade, Security/Privacy.
'@

Write-Doc "projects/_template/project.yaml" @'
id: replace-me
name: "Preencher"
version: 0.1.0
status: draft
project_type: software
workflow_id: software-project
sponsor: TODO
product_owner: TODO
data_classification: TODO
success_criteria: []
open_questions: []
'@
Write-Doc "projects/_template/README.md" @'
# Template de Projeto

Copie esta pasta, preencha `project.yaml`, registre o brief em `intake/` e mantenha artefatos em sua fase. `decisions/` contém ADRs; `logs/` contém eventos permitidos; `reports/` contém validações e status. Não registre segredos.
'@
$projectDirs=@("intake","business-analysis","architecture","planning","design","engineering","testing","security","deployment","documentation","decisions","logs","reports","retrospective")
foreach($d in $projectDirs){Write-Doc "projects/_template/$d/README.md" "# $d`n`nArtefatos do projeto relativos a $d. Todo arquivo deve ter dono, versão, status e origem."}

Write-Doc "clients/_template/client.yaml" @'
id: replace-me
name: "Preencher"
status: prospect
data_classification: confidential
relationship_owner: TODO
approved_systems: []
'@
Write-Doc "clients/_template/README.md" @'
# Template de Cliente

Guarda metadados mínimos e referências a sistemas aprovados. Não armazene segredos, credenciais, dados pessoais desnecessários ou conteúdo contratual restrito neste repositório.
'@
foreach($d in @("contacts","discovery","agreements","communications")){Write-Doc "clients/_template/$d/README.md" "# $d`n`nRegistre somente referências ou conteúdo autorizado, minimizado e classificado."}

Write-Doc "memory/README.md" @'
# Memória Organizacional

Entram somente decisões generalizáveis, lições confirmadas, padrões recorrentes, anti-patterns, incidentes sanitizados, definições de métricas e ativos reutilizáveis. Propostas precisam de fonte, revisão do dono do domínio e aprovação de Security/Privacy quando derivadas de clientes. Use SemVer, status e data; itens substituídos permanecem com link ao sucessor. Consultas devem considerar status e aplicabilidade. Deprecação registra motivo e alternativa. Conteúdo global nunca inclui identidade, segredo, contrato ou contexto confidencial de cliente; isso permanece no projeto e nos sistemas autorizados.
'@
$memoryDirs=@("decisions","lessons-learned","patterns","anti-patterns","incidents","metrics","reusable-assets")
foreach($d in $memoryDirs){Write-Doc "memory/$d/README.md" "# Memória: $d`n`nItens validados de $d. Cada registro contém fonte sanitizada, evidência, aplicabilidade, aprovador, versão, status e data de revisão."}

Write-Doc "observability/README.md" @'
# Observability da ASEP

A observabilidade documenta eventos de execução, métricas de fluxo, tracing entre projeto/workflow/tarefa/artefato e auditoria de decisões. A especificação não implementa coleta. Logs não contêm prompts integrais, segredos ou dados pessoais desnecessários.
'@
Write-Doc "observability/logging.md" "# Logging`n`nEventos estruturados usam o catálogo, timestamp UTC, IDs de correlação, ator, resultado e classificação. Mensagens são úteis sem conteúdo sensível; retenção e acesso seguem classificação."
Write-Doc "observability/metrics.md" "# Métricas`n`nMedir lead time por estágio, tempo bloqueado, taxa e causa de retorno, gates aprovados/reprovados, handoffs rejeitados, decisões pendentes e incidentes. Cada métrica possui fórmula, fonte, janela, dono e finalidade; não medir produtividade individual por volume."
Write-Doc "observability/tracing.md" "# Tracing`n`n`trace_id` representa uma execução; `project_id`, `workflow_run_id`, `stage_run_id`, `task_id`, `agent_run_id` e `artifact_id` permitem seguir causalidade. Retornos e retries preservam o trace e usam nova tentativa."
Write-Doc "observability/audit.md" "# Auditoria`n`nAuditar quem solicitou, executou, aprovou e alterou; versões de contrato/workflow; eventos; evidências; exceções e acesso. Registros são append-only no Runtime futuro, com retenção e integridade proporcionais ao risco."
Write-Doc "observability/status-model.md" @'
# Modelo de Status

Transições: `planned → ready → running`; `running → awaiting_approval|blocked|failed|completed|cancelled`; `blocked → ready|cancelled`; `failed → ready|cancelled`; `awaiting_approval → running|completed|blocked|cancelled`. Toda transição registra ator, motivo, timestamp e evidência. `completed` e `cancelled` são terminais; retomada cria nova execução vinculada.
'@
$events=@("project.created","workflow.started","workflow.completed","stage.started","stage.blocked","stage.failed","stage.completed","agent.started","agent.completed","quality_gate.failed","quality_gate.approved","human_approval.requested","human_approval.completed","artifact.created","decision.recorded","project.completed","project.cancelled")
Write-Doc "observability/event-catalog.yaml" ("version: 0.1.0`nrequired_fields: [event_id, event_type, occurred_at, actor_id, actor_type, project_id, trace_id, correlation_id, source, schema_version, data_classification, payload]`nevents:`n" + (($events | ForEach-Object {"  - type: $_`n    description: `"Records $_ transition`""}) -join "`n"))

$orchDocs=@{
"README"="Responsabilidade, limites e interação com Registry/Runtime";
"intake"="recebimento, autorização, classificação e registro da demanda";
"classification"="tipo de projeto, risco, dados, complexidade e urgência";
"routing"="seleção de workflow e agentes por capacidade, contrato e segregação";
"execution"="criação de tarefas, dependências, gates, aprovações e consolidação";
"state-management"="estado versionado, transições, bloqueios, cancelamento e retomada";
"error-handling"="classificação, retry seguro, correção, falha, preservação e escalonamento";
"human-approval"="pedido estruturado, autoridade, alternativas, prazo, decisão e auditoria"
}
foreach($k in $orchDocs.Keys){Write-Doc "orchestrator/$k.md" @"
# Orchestrator — $k

## Finalidade
Especificar $($orchDocs[$k]).
## Regras
Consultar Registry; fixar versões; validar dependências; não criar requisitos nem substituir especialista; manter segregação de funções; registrar eventos e decisões; bloquear sem evidência.
## Entradas e saídas
Recebe projeto, contexto autorizado e estado. Produz tarefas, roteamento, solicitações de aprovação, eventos, consolidação e handoff.
## Falhas
Preservar contexto, registrar causa, tentar apenas ação segura/idempotente e escalar com opções.
## Implementação futura
TODO(Runtime Owner): definir schema persistente, controle de concorrência, identidade e APIs após ADR e aprovação humana.
"@}

$runtimeDocs=@("README","agent-lifecycle","context-loading","input-validation","execution","self-review","artifact-generation","output-validation","state")
foreach($r in $runtimeDocs){Write-Doc "runtime/$r.md" @"
# Runtime — $r

## Objetivo
Especificar o comportamento implementável do Runtime sem integrar modelos de IA.
## Ciclo
Load → Validate → Load Contract → Load Knowledge → Load Standards → Load Context → Execute → Self Review → Quality Validation → Generate Artifacts → Handoff → Finish.
## Contrato
Cada passo recebe estado imutável/versionado, emite eventos, valida autorização e produz resultado explícito. Falha não avança silenciosamente.
## Segurança e estado
Contexto usa minimização e escopo; contratos/workflows têm versão fixada; artefatos têm checksum e origem; transições seguem `observability/status-model.md`.
## Critérios de implementação futura
Schemas, idempotência, concorrência, isolamento, auditoria, testes de contrato, recuperação e ADR aprovados.
"@}

Write-Doc "planning/ROADMAP.md" @'
# Roadmap ASEP 1.0

| Release | Resultado | Gate |
|---|---|---|
| 0.1 | Fundação documental | auditoria e navegação válidas |
| 0.2 | Registry e contratos | catálogos e interfaces consistentes |
| 0.3 | Workflows declarativos | schemas, condições e gates validados |
| 0.4 | Orchestrator mínimo | ADR, estado e coordenação testados |
| 0.5 | Runtime de agentes | lifecycle e isolamento verificáveis |
| 0.6 | Projeto piloto | execução assistida e métricas |
| 1.0 | Primeira versão utilizável | aceite do piloto e operação documentada |
'@
Write-Doc "planning/BACKLOG.md" @'
# Backlog ASEP 1.0

| Épico | Funcionalidade | Descrição | Prioridade | Dependências | Critérios de aceite | Status | Evidência esperada |
|---|---|---|---|---|---|---|---|
| Fundação | Modelo documental | Core, organização e navegação | Must | nenhuma | links e auditoria válidos | done | relatório |
| Catálogo | Registry | descoberta de componentes | Must | fundação | caminhos e IDs válidos | done | validação YAML |
| Interfaces | Contratos | contratos de 15 agentes | Must | catálogo | schemas e encadeamento válidos | done | matriz de contratos |
| Fluxo | Workflows | sete tipos declarativos | Must | gates/contratos | agentes e gates existentes | done | validação cruzada |
| Execução | Schema formal | JSON Schema/YAML Schema versionado | Must | workflows | exemplos passam/falham corretamente | planned | testes |
| Orchestrator | Estado mínimo | tarefas, transições e aprovações | Must | schema, ADR | cenários de bloqueio/retomada passam | planned | testes de aceitação |
| Runtime | Lifecycle | execução isolada por contrato | Must | orchestrator | lifecycle auditável | planned | traces |
| Segurança | Threat model | riscos do Runtime | Must | arquitetura | controles e riscos aprovados | planned | threat model |
| Piloto | Self-development | executar ASEP sobre si | Must | runtime mínimo | métricas e retrospectiva | planned | relatório piloto |
| Release | 1.0 | pacote utilizável e handover | Must | piloto | gates de release e aceite | planned | release report |
'@
Write-Doc "planning/RELEASES.md" "# Releases`n`nReleases seguem SemVer, changelog, compatibilidade, migração e aprovação. A 0.1 é documental; 0.2–0.3 consolidam declarativos; 0.4–0.5 implementam após aprovação; 0.6 pilota; 1.0 exige aceite."
Write-Doc "planning/RISKS.md" @'
# Riscos

| Risco | Impacto | Resposta | Dono | Gatilho |
|---|---|---|---|---|
| documentação parecer execução real | alto | status explícito e piloto | Product | promessa operacional |
| divergência entre catálogos | alto | validação automatizada | Tech Lead | alteração de ID |
| excesso de processo | médio | tailoring registrado | Delivery | lead time sem valor |
| dados de cliente na memória | alto | segregação e revisão | Security | proposta de memória |
| autoridade ambígua | alto | matriz e decisão humana | Executive | conflito |
'@
Write-Doc "planning/DEPENDENCIES.md" "# Dependências`n`nA implementação futura depende de ADRs de estado, identidade, armazenamento, schemas, isolamento, modelo de autorização, provedor de execução e orçamento. O piloto depende de responsáveis humanos nomeados e critérios aprovados."

Write-Doc "projects/asep-self-development/project.yaml" @'
id: asep-self-development
name: "ASEP Self-development"
version: 0.1.0
status: discovery
project_type: software
workflow_id: software-project
sponsor: TODO-human-owner
product_owner: TODO-human-owner
data_classification: internal
success_criteria:
  - "executar um ciclo assistido com rastreabilidade"
open_questions:
  - "Quem exercerá Sponsor, Product Manager, Tech Lead e Quality Lead?"
  - "Qual será o primeiro incremento implementável após aprovação?"
'@
Write-Doc "projects/asep-self-development/README.md" @'
# ASEP Self-development

## Objetivo
Usar a ASEP para especificar e, após aprovação futura, desenvolver a própria ASEP.
## Escopo
Nesta etapa, somente estrutura, perguntas, riscos e artefatos documentais; sem Runtime ou integração de IA.
## Workflow
`software-project`, versão 0.1.0.
## Agentes
Orchestrator, Business Analyst, Software Architect, Project Manager, QA, Security, DevOps e Documentation; especialistas adicionais serão condicionais.
## Entregáveis
Brief, análise validada, arquitetura/ADRs, plano, evidência, relatórios e retrospectiva.
## Critérios de sucesso
Contexto rastreável, decisões humanas nomeadas, workflow executável sem referências quebradas e piloto futuro mensurável.
## Perguntas pendentes
Quem assume papéis humanos? Qual ambiente e orçamento? Qual nível de autonomia? Quais dados e integrações podem ser usados?
## Próximos passos
Validar brief e decisões abertas; não iniciar código até aprovação humana.
'@
Write-Doc "projects/asep-self-development/intake/project-brief.md" @'
# Project Brief — ASEP Self-development

**Status:** draft | **Dono:** TODO Product Manager | **Data:** 2026-07-28

## Problema
A plataforma documental precisa provar que orienta uma execução real sem depender de conhecimento tácito.
## Resultado desejado
Um ciclo piloto assistido, auditável e mensurável.
## Escopo atual
Estrutura e preparação documental.
## Não escopo
Implementação de Runtime, Orchestrator ou integração com modelos.
## Hipóteses
A estrutura declarativa é suficiente para iniciar o desenho técnico; validar no piloto.
## Perguntas
Autoridades humanas, orçamento, ambiente, autonomia e primeiro caso de uso permanecem pendentes.
'@
foreach($d in @("business-analysis","architecture","planning","decisions","logs","reports")){Write-Doc "projects/asep-self-development/$d/README.md" "# $d`n`nÁrea reservada aos artefatos do piloto. Não contém requisito definitivo; novos itens exigem fonte, dono e status."}

Write-Doc "docs/README.md" @'
# Documentação de Apoio

Esta pasta preserva documentos úteis anteriores: glossário, métricas, catálogo de serviços e governança histórica. O Core canônico está em `../core/`; em conflito, prevalece `core/SYSTEM.md` e `core/GOVERNANCE.md`. Conteúdo histórico não deve ser duplicado: vincule-o quando ainda aplicável.
'@
Write-Doc "agents/README.md" "# Agentes`n`nManuais operacionais com 27 seções comuns. Interfaces ficam em ``contracts/``; catálogo em ``registry/agents.yaml``. Arquivos agrupados anteriores foram preservados como referências históricas, mas não são agentes registráveis."
Write-Doc "knowledge/README.md" "# Knowledge Base`n`nConhecimento orienta decisões; não define autoridade nem sequência. Cada área liga conceitos a agentes, workflows, standards e referências internas. Conteúdo entra na memória somente após validação."
Write-Doc "playbooks/README.md" "# Playbooks`n`nProcedimentos operacionais por situação. Workflows decidem quando executar; contracts decidem interfaces; standards decidem regras; knowledge informa o julgamento."
Write-Doc "standards/README.md" "# Standards`n`nRegras de qualidade e consistência, tecnológicas apenas quando necessário. Cada standard separa obrigatório, recomendado, contextual e exceção. Catálogo: ``registry/standards.yaml``."
Write-Doc "templates/README.md" "# Templates`n`nModelos categorizados para artefatos de projetos. Copie, preencha campos orientativos, mantenha exemplos mínimos e nunca deixe placeholder silencioso. Catálogo: ``registry/templates.yaml``."
Write-Doc "projects/README.md" "# Projetos`n`nCada iniciativa aprovada possui pasta própria baseada em ``_template/``. Artefatos específicos ficam aqui; reutilizáveis globais seguem ``../artifacts/README.md``."
Write-Doc "clients/README.md" "# Clientes`n`nUma pasta por cliente baseada em ``_template/``. Armazene apenas metadados e referências autorizadas; não registre segredos ou dados pessoais desnecessários."

Write-Doc "reports/open-decisions.md" @'
# Decisões Humanas Pendentes

| Decisão | Contexto | Alternativas | Impacto | Recomendação | Urgência |
|---|---|---|---|---|---|
| Nomear autoridades ASEP | Papéis estão definidos, pessoas não | nomear responsáveis; manter TODO e bloquear implementação | sem donos não há aprovações válidas | nomear Sponsor, Product, Tech, Quality e Security antes da 0.2 | alta |
| Escolher tecnologia do Runtime | especificação é agnóstica | build próprio; motor existente; solução híbrida | custo, lock-in e segurança | ADR após requisitos do piloto | média |
| Definir primeiro incremento piloto | perguntas ainda abertas | validação documental; executor local; catálogo consultável | determina arquitetura e métricas | começar por validação documental automatizada | alta |
| Definir política de dados para ferramentas de IA | não há provedor aprovado | somente dados públicos; ambiente privado; fornecedores aprovados | privacidade e viabilidade | manter dados públicos/sintéticos até avaliação | alta |
'@

Write-Doc "reports/platform-audit.md" @'
# Auditoria da Plataforma

**Data:** 2026-07-28 | **Responsável:** agente de documentação | **Status:** concluída para versão 0.1.0

## Estrutura encontrada
Base com 58 arquivos: documentos institucionais, sete manuais/agregados de agentes, um contrato, knowledge fundamentals, playbooks de produtos, prompts, standards, templates e workflows agregados.

## Problemas identificados
Ausência de Core, Registry, lifecycle formal, maioria dos contratos, workflows YAML, organização, memória, observabilidade, runtime, planning e templates de projeto/cliente. Nome do produto divergente; estruturas de agentes inconsistentes; sobreposição potencial entre governança e documentos agregados; ausência de WORKFLOW/SYSTEM na raiz.

## Correções
Identidade ASEP consolidada; Core e organização definidos; 15 agentes e contratos alinhados; Registry criado; sete workflows declarativos e 20 operacionais; playbooks, knowledge, standards e templates fundamentais; estruturas de projeto/cliente, memória, observabilidade, Orchestrator, Runtime, planning e piloto.

## Inconsistências restantes
Documentos históricos agrupados em `agents/`, playbooks de produto e standards anteriores permanecem como referência, sem entrada no Registry. A implementação futura ainda precisa de schema formal e teste de ciclos baseado em artefatos.

## Riscos e recomendações
Risco de excesso documental e divergência manual. Automatizar schemas e validações na 0.2, nomear autoridades humanas e pilotar um fluxo pequeno antes de implementar motor completo.
'@

Write-Doc "reports/implementation-summary.md" @'
# Resumo de Implementação

**Data:** 2026-07-28 | **Versão:** 0.1.0

## Concluído
Fundação documental, Core, organização, agentes, contratos, Registry, workflows, playbooks, knowledge fundamental, standards, templates, estruturas de projetos/clientes, memória, observabilidade, especificações de Orchestrator/Runtime, planejamento e estrutura piloto.

## Parcial
Schemas executáveis formais, métricas reais e validação pelo projeto piloto aguardam releases seguintes. Documentos históricos foram preservados e classificados como apoio.

## Artefatos
Consulte a árvore resumida e as validações finais registradas ao fim deste relatório.

## Próximos passos
Nomear autoridades; aprovar decisões abertas; criar schemas; executar piloto documental; somente então autorizar código do Orchestrator/Runtime.
'@
