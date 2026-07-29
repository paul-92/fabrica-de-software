"""Correções documentais da auditoria de segunda passagem.

Este utilitário mantém documentos declarativos; não executa agentes e não contém
integração com modelos ou código do Runtime/Orchestrator.
"""

from __future__ import annotations

import pathlib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


AGENTS = {
    "orchestrator": {
        "role": "orchestrator",
        "department": "operations",
        "reports_to": "executive",
        "required": ["project-brief"],
        "produces": ["project-record", "workflow-run", "consolidated-handover"],
        "next": ["business-analyst"],
    },
    "business-analyst": {
        "role": "business-analysis",
        "department": "business",
        "required": ["project-brief"],
        "produces": ["requirements", "business-rules", "scope", "assumptions"],
        "next": ["software-architect", "ux-ui-designer"],
    },
    "software-architect": {
        "role": "architecture",
        "department": "architecture",
        "required": ["requirements", "business-rules", "scope"],
        "produces": ["architecture-document", "adr", "technical-constraints"],
        "next": [
            "project-manager",
            "database-engineer",
            "ai-engineer",
            "security-engineer",
        ],
    },
    "project-manager": {
        "role": "project-management",
        "department": "operations",
        "required": ["requirements", "scope", "architecture-document"],
        "produces": ["roadmap", "backlog", "risk-register", "delivery-plan"],
        "next": ["ux-ui-designer", "backend-engineer"],
    },
    "ux-ui-designer": {
        "role": "product-design",
        "department": "product-design",
        "required": ["requirements", "scope"],
        "produces": [
            "user-flows",
            "design-specification",
            "accessibility-review",
        ],
        "next": ["frontend-engineer", "mobile-engineer"],
    },
    "database-engineer": {
        "role": "database-engineering",
        "department": "data",
        "required": ["architecture-document", "requirements"],
        "produces": ["data-model", "database-design", "migration-plan"],
        "next": ["backend-engineer"],
    },
    "backend-engineer": {
        "role": "backend-engineering",
        "department": "engineering",
        "required": ["architecture-document", "requirements", "backlog"],
        "produces": [
            "backend-change",
            "api-implementation",
            "implementation-evidence",
        ],
        "next": ["qa-engineer"],
    },
    "frontend-engineer": {
        "role": "frontend-engineering",
        "department": "engineering",
        "required": [
            "design-specification",
            "architecture-document",
            "requirements",
        ],
        "produces": ["frontend-change", "ui-test-evidence", "implementation-evidence"],
        "next": ["qa-engineer"],
    },
    "mobile-engineer": {
        "role": "mobile-engineering",
        "department": "engineering",
        "required": [
            "design-specification",
            "architecture-document",
            "requirements",
        ],
        "produces": [
            "mobile-change",
            "mobile-test-evidence",
            "implementation-evidence",
        ],
        "next": ["qa-engineer"],
    },
    "ai-engineer": {
        "role": "ai-engineering",
        "department": "engineering",
        "required": ["architecture-document", "requirements"],
        "produces": [
            "ai-design",
            "evaluation-plan",
            "model-card",
            "implementation-evidence",
        ],
        "next": ["qa-engineer", "security-engineer"],
    },
    "qa-engineer": {
        "role": "quality-assurance",
        "department": "quality",
        "required": ["requirements", "implementation-evidence"],
        "produces": ["test-plan", "test-report", "release-recommendation"],
        "next": ["security-engineer", "devops-engineer"],
    },
    "security-engineer": {
        "role": "security-engineering",
        "department": "security",
        "required": ["architecture-document", "requirements"],
        "produces": ["threat-model", "security-review", "security-findings"],
        "next": ["devops-engineer"],
    },
    "devops-engineer": {
        "role": "devops-engineering",
        "department": "operations",
        "required": ["test-report", "security-review", "release-recommendation"],
        "produces": ["deployment-plan", "runbook", "deployment-evidence"],
        "next": ["documentation-engineer"],
    },
    "documentation-engineer": {
        "role": "documentation-engineering",
        "department": "documentation",
        "required": ["requirements", "architecture-document", "deployment-evidence"],
        "produces": ["user-guide", "technical-documentation", "handover"],
        "next": ["support-engineer"],
    },
    "support-engineer": {
        "role": "support-maintenance",
        "department": "operations",
        "required": ["handover", "runbook"],
        "produces": ["incident-record", "support-report", "maintenance-plan"],
        "next": [],
    },
}


def normalize_contracts() -> None:
    for agent_id, spec in AGENTS.items():
        path = ROOT / "contracts" / f"{agent_id}.yaml"
        contract = yaml.safe_load(path.read_text(encoding="utf-8"))
        contract["department"] = spec["department"]
        contract["role"] = spec["role"]
        contract["reports_to"] = spec.get("reports_to", "orchestrator")
        contract["receives"] = list(
            dict.fromkeys(spec["required"] + ["constraints", "decisions", "risk-register"])
        )
        contract["required_inputs"] = spec["required"]
        contract["produces"] = spec["produces"]
        contract["required_outputs"] = spec["produces"]
        contract["next_agents"] = spec["next"]
        path.write_text(
            yaml.safe_dump(
                contract, allow_unicode=True, sort_keys=False, width=1000
            ),
            encoding="utf-8",
        )


STANDARD_RULES = {
    "documentation": (
        "Todo documento informa público, objetivo, dono, status, versão e fontes.",
        "Arquitetura da informação, linguagem simples, exemplos curtos e teste com leitor representativo.",
        "Formato, profundidade e localização dependem de risco, vida útil e público.",
        "Evidência: revisão editorial, links válidos, termos do glossário e aceite do público responsável.",
    ),
    "naming": (
        "IDs e arquivos usam `kebab-case`; datas usam `YYYY-MM-DD`; IDs publicados não são reutilizados.",
        "Nomear pelo conceito de domínio, evitando abreviações locais e nomes de implementação.",
        "Convenções externas podem prevalecer em APIs, linguagens e plataformas, desde que documentadas.",
        "Evidência: lint ou revisão de nomes, glossário e mapa de renomeação quando houver quebra.",
    ),
    "versioning": (
        "Componentes registráveis usam SemVer; projeto fixa a versão executada; breaking change incrementa major.",
        "Manter changelog, janela de depreciação e compatibilidade retroativa quando viável.",
        "Artefatos internos podem usar versão documental incremental se não forem consumidos como contrato.",
        "Evidência: versão, diff, análise de compatibilidade, migração e aprovação do dono.",
    ),
    "repository-structure": (
        "Artefatos de projeto ficam em `projects/<id>`; globais aprovados em `artifacts/`; catálogo em `registry/`.",
        "Cada seção tem README ou navegação canônica e evita cópias divergentes.",
        "Subpastas adicionais são permitidas quando ownership, retenção e finalidade estiverem documentados.",
        "Evidência: árvore, links, ausência de pastas vazias e caminhos registrados existentes.",
    ),
    "requirements": (
        "Cada requisito tem ID, fonte, ator, necessidade, prioridade, status e critério de aceite observável.",
        "Separar requisito, regra, restrição, hipótese e solução; manter rastreabilidade bidirecional.",
        "User story, use case ou especificação tabular depende do tipo e complexidade do comportamento.",
        "Evidência: revisão de negócio, matriz requisito–critério–teste e decisões pendentes explícitas.",
    ),
    "architecture": (
        "Documentar contexto, atributos de qualidade, fronteiras, dados, dependências, falhas e operação.",
        "Comparar alternativas e favorecer modularidade, reversibilidade e evolução baseada em evidência.",
        "Estilo arquitetural e tecnologia dependem de escala, equipe, risco e restrições confirmadas.",
        "Evidência: documento, diagramas necessários, ADRs, threat model e revisão multidisciplinar.",
    ),
    "adr": (
        "ADR contém contexto, problema, alternativas, decisão, justificativa, consequências, riscos, responsáveis, data e status.",
        "Não reescrever decisão aceita; criar sucessor e ligar `supersedes/superseded-by`.",
        "ADR é obrigatório para decisão material, difícil de reverter, transversal ou que cria exceção.",
        "Evidência: aprovação do dono técnico e consultados, links aos requisitos e plano de saída.",
    ),
    "api": (
        "Contrato explicita autenticação, autorização, erros, idempotência, paginação, limites e versionamento.",
        "Validar compatibilidade do consumidor, correlation ID, observabilidade e política de depreciação.",
        "REST, GraphQL, RPC ou eventos dependem de semântica, consumidores, latência e evolução.",
        "Evidência: contrato validado, testes de contrato, casos de abuso e exemplos mínimos executáveis.",
    ),
    "database": (
        "Definir fonte de verdade, ownership, classificação, integridade, migrações, retenção, backup e restauração.",
        "Modelar por padrões de acesso confirmados e testar migração/rollback com volume representativo.",
        "Modelo relacional, documento, chave-valor ou analítico depende de consistência, consulta e operação.",
        "Evidência: modelo, dicionário, plano de migração, teste de restauração e controles de acesso.",
    ),
    "backend": (
        "Serviços validam entrada e autorização no servidor, preservam idempotência e emitem telemetria segura.",
        "Separar domínio de infraestrutura, limitar transações e tratar timeout, retry e falha parcial.",
        "Estrutura interna e estilo de serviço dependem da arquitetura aprovada.",
        "Evidência: revisão, análise estática, testes de unidade/integração/contrato e rastreabilidade.",
    ),
    "frontend": (
        "Interfaces cobrem estados vazio, carregando, sucesso, erro e permissão; cumprem acessibilidade aplicável.",
        "Manter semântica, navegação por teclado, feedback claro e orçamento de desempenho.",
        "Renderização e gerenciamento de estado dependem de SEO, interação, conectividade e equipe.",
        "Evidência: revisão visual, testes assistivos, jornadas críticas e métricas de desempenho.",
    ),
    "mobile": (
        "Tratar lifecycle, permissões, conectividade, armazenamento seguro, acessibilidade e políticas das lojas.",
        "Projetar modo degradado, consumo de recursos, atualização e compatibilidade de versões.",
        "Nativo ou multiplataforma depende de UX, integrações, equipe e ciclo de release.",
        "Evidência: testes em dispositivos representativos, políticas, telemetria e plano de rollout.",
    ),
    "ai": (
        "Definir finalidade, limites, dados autorizados, avaliação, supervisão, fallback e comunicação de incerteza.",
        "Versionar modelo/prompt/dataset, testar abuso, drift, vieses relevantes e falhas previsíveis.",
        "Modelo, RAG, fine-tuning ou regra determinística dependem de valor, risco, dados e custo.",
        "Evidência: evaluation plan, model card, conjunto versionado, resultados e aceite de risco.",
    ),
    "testing": (
        "Testes cobrem critérios e riscos; resultados registram ambiente, versão, dados, execução e defeitos.",
        "Priorizar feedback rápido: unidade para lógica, integração para fronteiras e E2E para jornadas críticas.",
        "Níveis, automação e testes não funcionais dependem de risco e arquitetura.",
        "Evidência: estratégia, matriz de cobertura de risco, relatório reproduzível e risco residual.",
    ),
    "security": (
        "Aplicar menor privilégio, deny-by-default, proteção de segredos, classificação e validação de entrada.",
        "Modelar ameaças, testar autorização e supply chain, definir retenção e resposta a incidentes.",
        "Controles concretos dependem de dados, exposição, ameaças e obrigações aplicáveis.",
        "Evidência: threat model, achados priorizados, verificação de controles e aceite autorizado.",
    ),
    "devops": (
        "Ambientes são reproduzíveis; deploy é observável e reversível; segredos nunca ficam no repositório.",
        "Automatizar checks, separação de funções, backup/restauração e rollout progressivo.",
        "Plataforma e topologia dependem de SLO, capacidade, risco, equipe e custo total.",
        "Evidência: pipeline, plano de deploy, rollback exercitado, runbook e go/no-go.",
    ),
    "observability": (
        "Logs, métricas e traces usam IDs de correlação, classificação e retenção; alertas são acionáveis.",
        "Instrumentar jornadas e dependências críticas, ligando alerta a dashboard e runbook.",
        "Sinais e granularidade dependem de SLO, risco, custo e necessidades de diagnóstico.",
        "Evidência: catálogo de eventos, consultas/dashboards, teste de alerta e ausência de dados indevidos.",
    ),
    "code-review": (
        "Mudança material recebe revisão independente; autor responde achados e não autoaprova conflito.",
        "Revisar correção, segurança, testes, legibilidade, operação, compatibilidade e escopo.",
        "Número de revisores e especialistas depende do risco e ownership.",
        "Evidência: diff rastreável, checks, comentários resolvidos e aprovações registradas.",
    ),
    "git": (
        "Commits são focados, rastreáveis e sem segredos; branch protegida exige checks e revisão.",
        "Mensagens explicam intenção; histórico preserva autoria e não mistura mudanças alheias.",
        "Estratégia de branch e merge depende do fluxo de release e requisitos de auditoria.",
        "Evidência: histórico, vínculo com tarefa, checks e assinatura quando exigida.",
    ),
}


def rewrite_standards() -> None:
    for standard, (required, recommended, contextual, evidence) in STANDARD_RULES.items():
        write(
            f"standards/{standard}.md",
            f"""
# Standard: {standard}

**Dono:** responsável do domínio | **Versão:** 0.1.1 | **Status:** ativo

## Regra obrigatória

- {required}
- Toda exceção registra regra afetada, motivo, risco, aprovador, escopo, validade e plano de remoção.

## Recomendação

- {recommended}

## Opção dependente do contexto

- {contextual}

## Evidência obrigatória

- {evidence}

## Quality gate e relações

O agente responsável verifica este standard no gate da fase definido em
[`core/QUALITY.md`](../core/QUALITY.md). Decisões materiais seguem
[`core/DECISIONS.md`](../core/DECISIONS.md); mudanças seguem
[`core/CHANGE-MANAGEMENT.md`](../core/CHANGE-MANAGEMENT.md).
""",
        )


RUNTIME = {
    "README": (
        "delimitar o executor futuro e suas fronteiras",
        "Recebe uma tarefa imutável, fixa versões de contrato/workflow, executa o lifecycle e devolve estado, eventos e artefatos.",
        "Não seleciona produto, não aprova risco e não altera contratos durante uma execução.",
    ),
    "agent-lifecycle": (
        "definir estados e transições de uma execução de agente",
        "`created → loading → validating → executing → reviewing → validating_output → handing_off → completed`; qualquer estado ativo pode ir a `blocked`, `failed` ou `cancelled`.",
        "Cada transição exige precondição, timestamp, ator, motivo e evento; retry cria `attempt` novo.",
    ),
    "context-loading": (
        "carregar apenas contexto autorizado e necessário",
        "Resolver projeto, tarefa, versões, artefatos por ID, classificação, escopo e limite de tamanho; registrar origem e checksum.",
        "Conteúdo não autorizado, versão ambígua ou dado sensível fora de política bloqueia o carregamento.",
    ),
    "input-validation": (
        "impedir execução com entradas incompatíveis",
        "Validar schema, required inputs do contrato, produtor/origem, versão, integridade, autorização e consistência entre IDs.",
        "Lacuna crítica bloqueia; lacuna não crítica só vira hipótese com impacto, dono e gatilho explícitos.",
    ),
    "execution": (
        "especificar a unidade segura de execução",
        "Criar `agent_run_id`, fornecer contexto mínimo, aplicar limites, capturar ferramentas autorizadas e emitir heartbeat/eventos.",
        "Timeout, cancelamento e falha parcial preservam estado; efeitos externos exigem idempotency key e autorização.",
    ),
    "self-review": (
        "tornar a revisão do próprio agente verificável",
        "Comparar saída com objetivo, contrato, fontes, standards, critérios e riscos; listar falhas corrigidas e pendências.",
        "Self-review não substitui revisor independente nem pode aprovar conflito de interesse.",
    ),
    "artifact-generation": (
        "padronizar criação e versionamento de artefatos",
        "Artefato recebe ID, tipo, versão, status, produtor, fontes, classificação, checksum, projeto e links de decisão.",
        "Escrita é atômica; substituição cria nova versão; artefato global exige sanitização e aprovação.",
    ),
    "output-validation": (
        "garantir compatibilidade entre produtor e consumidor",
        "Validar required outputs, schema, nomes canônicos, links, classificação, evidências do gate e required inputs dos próximos agentes.",
        "Saída inválida retorna para correção com achados estruturados; ausência nunca é sucesso.",
    ),
    "state": (
        "definir o estado mínimo persistente",
        "Projeto, workflow run, stage run, task, agent run, approval, gate, artifact e event têm IDs estáveis, versão e relações causais.",
        "Atualizações usam controle de concorrência; histórico é append-only para auditoria; retenção segue classificação.",
    ),
}


def rewrite_runtime() -> None:
    for name, (goal, behavior, guard) in RUNTIME.items():
        write(
            f"runtime/{name}.md",
            f"""
# Runtime — {name}

**Status:** especificação | **Versão:** 0.1.1 | **Dono:** Runtime Owner a nomear

## Objetivo

{goal.capitalize()} sem integrar modelos de IA nesta versão.

## Comportamento especificado

{behavior}

## Invariantes e falhas

{guard} Falhas emitem evento, preservam causa e não avançam o estado silenciosamente.

## Entradas e saídas

Entradas carregam IDs, versões, classificação e autorização. Saídas incluem estado,
eventos, artefatos ou erro tipado, além de correlação com a tarefa.

## Critérios para implementação futura

- schema versionado e testes de contrato;
- idempotência, concorrência e recuperação verificadas;
- isolamento e modelo de autorização aprovados por Security;
- ADR aceito antes de escolher tecnologia.

## Referências

[`core/SYSTEM.md`](../core/SYSTEM.md),
[`runtime/agent-lifecycle.md`](agent-lifecycle.md) e
[`observability/status-model.md`](../observability/status-model.md).
""",
        )


WORKFLOWS = {
    "project-intake": ("registrar e qualificar a demanda", "project-brief", "QG-INTAKE", "orchestrator", "projeto classificado e decisão de discovery"),
    "new-client": ("criar contexto segregado do cliente", "client-record", "QG-INTAKE", "orchestrator", "cliente identificado, classificação e sistemas autorizados"),
    "new-project": ("instanciar projeto e fixar workflow", "project-record", "QG-INTAKE", "orchestrator", "estrutura criada, owners e versão fixados"),
    "discovery": ("investigar problema, usuários e evidências", "discovery-synthesis", "QG-DISCOVERY", "business-analyst", "hipóteses e recomendação validadas"),
    "business-analysis": ("formalizar requisitos, regras e escopo", "requirements", "QG-ANALYSIS", "business-analyst", "requisitos rastreáveis e aprovados"),
    "architecture": ("definir solução e trade-offs técnicos", "architecture-document", "QG-ARCH", "software-architect", "ADRs, fronteiras, falhas e riscos revisados"),
    "planning": ("planejar incrementos, capacidade e dependências", "delivery-plan", "QG-PLAN", "project-manager", "backlog executável e riscos com dono"),
    "product-design": ("projetar jornadas, estados e acessibilidade", "design-specification", "QG-DESIGN", "ux-ui-designer", "design validado contra requisitos"),
    "implementation": ("produzir incremento integrado", "implementation-evidence", "QG-IMPLEMENT", "engineering-specialist", "critérios implementados e checks aprovados"),
    "code-review": ("realizar revisão independente da mudança", "review-record", "QG-IMPLEMENT", "reviewer-independent", "achados resolvidos ou aceitos por autoridade"),
    "testing": ("validar critérios e riscos", "test-report", "QG-TEST", "qa-engineer", "resultados reproduzíveis e risco residual registrado"),
    "security-review": ("avaliar ameaças e controles", "security-review", "QG-SECURITY", "security-engineer", "nenhum bloqueador aberto"),
    "deployment": ("liberar de forma observável e reversível", "deployment-evidence", "QG-DEPLOY", "devops-engineer", "go/no-go, smoke test e observação registrados"),
    "documentation": ("atualizar informação para usuários e operação", "technical-documentation", "QG-DOC", "documentation-engineer", "documentação revisada pelo público responsável"),
    "handover": ("transferir ativos e responsabilidade", "handover", "QG-HANDOVER", "orchestrator", "receptor confirma completude e ownership"),
    "maintenance": ("tratar evolução e saúde do serviço", "maintenance-plan", "QG-CLOSE", "support-engineer", "mudança ou ação operacional rastreável"),
    "change-request": ("avaliar alteração material", "change-request", "QG-PLAN", "project-manager", "impacto e decisão autorizada registrados"),
    "incident-response": ("conter, recuperar e aprender com incidente", "incident-record", "QG-CLOSE", "support-engineer", "serviço estabilizado e ações com dono"),
    "project-closure": ("encerrar obrigações e estado do projeto", "closure-report", "QG-CLOSE", "orchestrator", "aceite, retenção e pendências transferidos"),
    "retrospective": ("converter evidência do ciclo em ações", "retrospective", "QG-CLOSE", "project-manager", "ações priorizadas com dono e prazo"),
}

WORKFLOW_STEPS = {
    "project-intake": ["registrar origem, sponsor, urgência e resultado", "classificar dados e tipo de projeto", "verificar autoridade, restrições e conflitos", "recomendar avançar, esclarecer, aguardar ou recusar"],
    "new-client": ["atribuir ID e relationship owner", "classificar dados e canais autorizados", "registrar referências a acordos e sistemas oficiais", "confirmar segregação antes de abrir projeto"],
    "new-project": ["copiar a estrutura-modelo", "atribuir ID, tipo, owner e classificação", "fixar workflow e versões dos componentes", "criar estado inicial e evento project.created"],
    "discovery": ["definir perguntas e métodos", "consultar participantes e fontes autorizadas", "sintetizar fatos, hipóteses e contradições", "validar problema e recomendação com decisores"],
    "business-analysis": ["mapear stakeholders e processo atual", "catalogar requisitos, regras e restrições", "delimitar escopo/MVP sem prescrever tecnologia", "validar critérios e rastreabilidade"],
    "architecture": ["identificar drivers e atributos de qualidade", "modelar contexto, fronteiras, dados e falhas", "comparar alternativas e estratégia de saída", "registrar ADRs e revisão multidisciplinar"],
    "planning": ["fatiar resultados em incrementos", "estimar por faixas e explicitar premissas", "mapear capacidade, dependências e caminho crítico", "definir gatilhos de replanejamento"],
    "product-design": ["validar usuários e jornadas prioritárias", "desenhar fluxos, estados e conteúdo", "avaliar acessibilidade e alternativas", "especificar e validar com critérios"],
    "implementation": ["refinar critério e contrato da mudança", "implementar incremento pequeno", "instrumentar erros e sinais aplicáveis", "executar checks e preparar revisão"],
    "code-review": ["confirmar escopo e independência do revisor", "inspecionar correção, segurança e compatibilidade", "verificar testes, operação e documentação", "classificar e encerrar achados"],
    "testing": ["mapear requisitos e riscos a técnicas", "preparar ambiente e dados autorizados", "executar e preservar resultados reproduzíveis", "classificar defeitos e recomendar release"],
    "security-review": ["classificar ativos, dados e fronteiras", "modelar ameaças e caminhos de abuso", "verificar controles e supply chain", "priorizar achados e risco residual"],
    "deployment": ["confirmar versão, janela, owners e go/no-go", "validar migração, backup e rollback", "liberar progressivamente e executar smoke tests", "observar thresholds e comunicar resultado"],
    "documentation": ["identificar públicos e tarefas", "comparar comportamento com fontes", "atualizar guias, referência e runbook", "testar navegação, links e exemplos"],
    "handover": ["inventariar ativos, acessos e ownership", "demonstrar operação e decisões", "transferir riscos e pendências com dono", "obter confirmação explícita do receptor"],
    "maintenance": ["qualificar sinal, defeito ou mudança", "avaliar impacto, prioridade e risco", "executar change workflow ou runbook", "medir resultado e atualizar conhecimento"],
    "change-request": ["registrar pedido, motivo e solicitante", "avaliar valor, prazo, custo, arquitetura e risco", "comparar trocar escopo, prazo, capacidade ou rejeitar", "obter decisão e atualizar baselines"],
    "incident-response": ["classificar severidade e assumir comando", "conter impacto e preservar evidência", "recuperar com procedimento seguro", "comunicar, analisar fatores e acompanhar ações"],
    "project-closure": ["confirmar aceite e obrigações", "transferir ativos, acessos e pendências", "revisar retenção, custos e métricas", "encerrar estado e registrar lições propostas"],
    "retrospective": ["reunir resultados e eventos do ciclo", "identificar fatores que ajudaram ou dificultaram", "separar observação de interpretação", "priorizar poucas ações com dono e prazo"],
}


def rewrite_workflows() -> None:
    for name, (goal, artifact, gate, owner, completion) in WORKFLOWS.items():
        steps = "\n".join(
            f"{index}. {step.capitalize()}."
            for index, step in enumerate(WORKFLOW_STEPS[name], start=1)
        )
        write(
            f"workflows/{name}.md",
            f"""
# Workflow: {name}

**Dono:** {owner} | **Versão:** 0.1.1 | **Status:** ativo

## Objetivo e quando usar

{goal.capitalize()}. Executar quando o lifecycle, uma condição do workflow
declarativo ou uma decisão registrada exigir esta fase.

## Pré-condições e entradas

- projeto e execução identificados;
- contrato do agente, versões e autoridade válidos;
- artefatos predecessores exigidos pelo contrato;
- restrições, riscos e decisões relevantes carregados.

Entrada principal esperada: artefatos predecessores necessários para produzir
`{artifact}`. Entrada incompatível gera `stage.blocked`, não hipótese silenciosa.

## Procedimento específico

{steps}
5. Produzir e versionar `{artifact}`, ligando fontes e decisões.
6. Fazer self-review e obter revisão independente quando o risco exigir.
7. Avaliar `{gate}` e emitir handoff, eventos e próxima ação.

## Condições, bloqueio e retorno

Etapa pode ser omitida somente quando o workflow permitir e houver justificativa
aprovada. Bloqueio registra causa, impacto, dono e gatilho. Retorno preserva versão
e histórico. Cancelamento preserva auditoria e deveres de retenção.

## Aprovação humana

Obrigatória quando houver mudança material de escopo, custo ou prazo, produção,
acesso sensível, exceção, decisão irreversível ou risco residual alto.

## Saída, gate e conclusão

Saída principal: `{artifact}` com evidências, riscos, decisões e handoff.
Gate: `{gate}`. Conclui quando {completion}.

## Referências

[`core/LIFECYCLE.md`](../core/LIFECYCLE.md),
[`core/QUALITY.md`](../core/QUALITY.md) e
[`core/COMMUNICATION.md`](../core/COMMUNICATION.md).
""",
        )


TEMPLATE_SECTIONS = {
    "project-brief": ["Problema e evidência", "Público e resultado", "Escopo e não escopo", "Sponsor e decisões", "Restrições e hipótese de valor"],
    "executive-summary": ["Decisão solicitada", "Situação atual", "Opções e recomendação", "Impacto e risco", "Próxima ação"],
    "stakeholder-map": ["Grupos e papéis", "Interesse e influência", "Direitos de decisão", "Informação que confirmam", "Plano de participação"],
    "personas": ["Evidências usadas", "Objetivos e tarefas", "Contexto e limitações", "Necessidades de acessibilidade", "Hipóteses a validar"],
    "requirements": ["Catálogo de requisitos", "Requisitos não funcionais", "Critérios de aceite", "Rastreabilidade", "Lacunas e conflitos"],
    "business-rules": ["Catálogo de regras", "Fonte e autoridade", "Condições e exceções", "Vigência e precedência", "Requisitos afetados"],
    "user-stories": ["Épico e objetivo", "Stories e valor", "Critérios de aceite", "Dependências", "Definition of Ready"],
    "scope": ["Objetivo do recorte", "Incluído", "Não incluído", "Premissas e restrições", "Controle de mudanças"],
    "risks": ["Escala de avaliação", "Registro de riscos", "Respostas e donos", "Gatilhos", "Risco residual"],
    "assumptions": ["Premissas", "Impacto se falsas", "Plano de validação", "Dono e prazo", "Resultado da validação"],
    "architecture-document": ["Contexto e atributos", "Fronteiras e componentes", "Dados e integrações", "Falhas e segurança", "Operação, custo e ADRs"],
    "adr": ["Contexto e problema", "Alternativas", "Decisão e justificativa", "Consequências e riscos", "Status e supersessão"],
    "api-contract": ["Consumidores e casos", "Operações e schemas", "Identidade e autorização", "Erros e idempotência", "Versionamento e observabilidade"],
    "database-design": ["Ownership e classificação", "Modelo conceitual/lógico", "Integridade e acesso", "Migração e retenção", "Backup, restauração e capacidade"],
    "technical-roadmap": ["Resultado e horizonte", "Incrementos", "Dependências", "Capacidade e premissas", "Gatilhos de replanejamento"],
    "backlog": ["Objetivo do backlog", "Itens priorizados", "Critérios de aceite", "Dependências e riscos", "Política de refinamento"],
    "test-plan": ["Escopo e riscos", "Níveis e técnicas", "Ambientes e dados", "Matriz requisito–teste", "Entrada, saída e automação"],
    "test-report": ["Versão e ambiente", "Execuções e resultados", "Defeitos", "Cobertura de risco", "Recomendação e risco residual"],
    "security-review": ["Escopo e ativos", "Threat model", "Controles verificados", "Achados e severidade", "Risco residual e aprovação"],
    "deployment-plan": ["Versão e janela", "Precondições", "Migração e rollout", "Smoke tests e observação", "Pausa, rollback e comunicação"],
    "runbook": ["Serviço e ownership", "SLOs e dashboards", "Alertas e diagnóstico", "Procedimentos seguros", "Escalonamento e recuperação"],
    "user-guide": ["Público e pré-requisitos", "Jornadas", "Estados e erros", "Acessibilidade e suporte", "Limites e segurança"],
    "handover": ["Contexto e estado", "Entradas e validações", "Artefatos e acessos", "Riscos e pendências", "Aceite e próxima ação"],
    "retrospective": ["Objetivo e período", "Resultados e evidências", "O que ajudou/dificultou", "Aprendizados", "Ações com dono"],
    "lessons-learned": ["Observação", "Evidência e confiança", "Aplicabilidade", "Recomendação", "Aprovação para memória"],
    "change-request": ["Pedido e motivo", "Impacto", "Alternativas", "Recomendação", "Decisão e atualizações"],
    "incident-report": ["Impacto e severidade", "Linha do tempo", "Contenção e recuperação", "Causas e fatores", "Ações e comunicação"],
}


def rewrite_templates() -> None:
    for path in (ROOT / "templates").rglob("*.md"):
        if path.name == "README.md" or path.parent == ROOT / "templates":
            continue
        template_id = path.stem
        if template_id not in TEMPLATE_SECTIONS:
            continue
        sections = "\n\n".join(
            f"## {section}\n\n[Preencher com informação rastreável; se desconhecida, registrar responsável e gatilho.]"
            for section in TEMPLATE_SECTIONS[template_id]
        )
        write(
            str(path.relative_to(ROOT)),
            f"""
# Template: {template_id}

> Copie para o projeto. Substitua campos entre colchetes, remova instruções e
> não deixe pendência sem dono e prazo ou gatilho.

**ID:** [identificador] | **Versão:** [semver] | **Status:** [draft/review/approved]  
**Dono:** [papel] | **Data:** [YYYY-MM-DD] | **Fontes:** [links]

## Objetivo do artefato

[Decisão, gate ou público que este artefato atende.]

{sections}

## Fatos, hipóteses e decisões

| Tipo | Declaração | Fonte ou dono | Status/gatilho |
|---|---|---|---|
| Exemplo mínimo | [remover] | [referência] | [estado] |

## Evidências e quality gate

| Critério | Evidência | Resultado | Avaliador |
|---|---|---|---|

## Riscos, pendências e handoff

| Item | Impacto | Próxima ação | Responsável | Prazo/gatilho |
|---|---|---|---|---|
""",
        )


def update_workflow_registry() -> None:
    path = ROOT / "registry" / "workflows.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    for item in registry["workflows"]:
        workflow = yaml.safe_load(
            (path.parent / item["path"]).resolve().read_text(encoding="utf-8")
        )
        item["agents"] = sorted(
            {
                agent
                for assigned in workflow["assigned_agents"].values()
                for agent in (assigned or [])
            }
        )
        item["gates"] = workflow["quality_gates"]
    path.write_text(
        yaml.safe_dump(registry, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )


def improve_folder_purpose() -> None:
    purposes = {
        "contacts": "Índice de papéis e canais autorizados; prefira IDs ou referências ao CRM, sem dados pessoais desnecessários.",
        "discovery": "Contexto inicial autorizado do cliente, separado dos artefatos de projetos específicos.",
        "agreements": "Referências a contratos, DPA, NDA e aprovações em sistemas oficiais; não copie conteúdo restrito.",
        "communications": "Registro de decisões e compromissos relevantes, com data, participantes por papel e link à fonte oficial.",
    }
    for folder, purpose in purposes.items():
        write(
            f"clients/_template/{folder}/README.md",
            f"""
# Cliente — {folder}

## Finalidade

{purpose}

## Pode conter

Metadados minimizados, dono, classificação, data, validade e links para sistemas
aprovados.

## Não pode conter

Credenciais, segredos, dados pessoais sem necessidade, cópias não autorizadas ou
artefatos que pertencem a `projects/<id>/`.
""",
        )

    project_purposes = {
        "intake": "demanda, autorização, classificação e Project Brief",
        "business-analysis": "requisitos, regras, escopo, stakeholders e critérios de aceite",
        "architecture": "arquitetura, diagramas, threat model e ADRs vinculados",
        "planning": "roadmap, backlog, estimativas, dependências e riscos",
        "design": "pesquisa autorizada, jornadas, especificações e acessibilidade",
        "engineering": "referências às mudanças, contratos e evidências de implementação",
        "testing": "estratégia, casos, dados autorizados, execuções e relatórios",
        "security": "threat model, revisões, achados e aceite de risco",
        "deployment": "plano, aprovações, migração, rollback e evidência de release",
        "documentation": "guias, documentação técnica e informação operacional",
        "decisions": "ADRs e decisões duráveis; decisões aceitas não são reescritas",
        "logs": "eventos permitidos e referências de execução, sem segredos ou prompts integrais",
        "reports": "status, auditorias, métricas e evidências consolidadas",
        "retrospective": "retrospectivas, ações e propostas de aprendizado",
    }
    for folder, purpose in project_purposes.items():
        write(
            f"projects/_template/{folder}/README.md",
            f"""
# Projeto — {folder}

## Finalidade

Esta pasta contém {purpose}.

## Regra de entrada

Todo artefato tem ID ou nome canônico, dono, versão, status, fontes, classificação
e relação com workflow/gate. Pendências têm responsável e prazo ou gatilho.

## Limites

Não duplicar artefato canônico de outra fase; use links. Não armazenar segredo,
dado pessoal desnecessário ou ativo reutilizável global.
""",
        )


def rewrite_observability_and_planning() -> None:
    documents = {
        "observability/README.md": """
# Observability da ASEP

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

A observabilidade descreve como uma execução futura poderá ser diagnosticada,
medida e auditada. Esta versão não implementa coleta.

| Componente | Finalidade |
|---|---|
| [logging.md](logging.md) | eventos diagnósticos estruturados e sanitizados |
| [metrics.md](metrics.md) | indicadores de fluxo, qualidade e confiabilidade |
| [tracing.md](tracing.md) | causalidade entre tarefa, agente, gate e artefato |
| [audit.md](audit.md) | autoridade, versões, decisões, acessos e integridade |
| [status-model.md](status-model.md) | estados e transições permitidas |
| [event-catalog.yaml](event-catalog.yaml) | tipos e campos mínimos de evento |

Logs não contêm prompts integrais, segredos ou dados pessoais desnecessários.
Eventos operacionais não substituem artefatos, ADRs ou aprovações formais.
""",
        "observability/logging.md": """
# Logging

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

## Estrutura obrigatória

Registros usam timestamp UTC, nível, componente, `event_type`, `trace_id`,
`correlation_id`, IDs de execução, ator não sensível, resultado, código de erro,
`schema_version` e classificação.

## Proteção

- mensagens descrevem evento e ação, não prompts integrais;
- segredos, tokens e payloads pessoais são removidos na origem;
- campos livres são limitados e normalizados;
- acesso, retenção, integridade e descarte seguem classificação;
- falha de redaction é incidente de segurança.

## Evidência

Schema validado, amostra sanitizada, teste de correlação, política de retenção e
consulta que reconstrói uma execução sem conteúdo confidencial.
""",
        "observability/metrics.md": """
# Métricas

**Dono:** Product + Operations | **Status:** especificação | **Versão:** 0.1.1

| Métrica | Definição | Uso |
|---|---|---|
| lead time | `completed_at - started_at`, por versão/tipo | previsibilidade |
| tempo bloqueado | soma dos intervalos em `blocked` | impedimentos |
| retorno por gate | retornos / avaliações | qualidade da entrada |
| handoff rejeitado | devoluções por incompatibilidade | qualidade contratual |
| decisão pendente | solicitações abertas por idade | governança |
| falha por estágio | `failed` por causa normalizada | confiabilidade |

Cada métrica registra fórmula, eventos-fonte, janela, dimensões permitidas, dono,
baseline, finalidade e limitações. Não medir produtividade individual por volume.
Validar completude, duplicidade, relógio, cardinalidade e mudanças de schema.
""",
        "observability/tracing.md": """
# Tracing

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

`trace_id` representa a execução ponta a ponta. `project_id`, `workflow_run_id`,
`stage_run_id`, `task_id`, `agent_run_id`, `approval_id`, `gate_evaluation_id`
e `artifact_id` reconstroem causalidade sem copiar conteúdo dos artefatos.

Cada etapa cria span com início, fim, status, versões e relações para sequência ou
paralelismo. Retorno preserva o trace; retry incrementa `attempt` e aponta para a
tentativa anterior. Operação externa registra apenas metadados permitidos.

Uma amostra deve permitir seguir demanda → agente → gate → artefato → handoff,
incluindo loops de correção e aprovações, sem expor dados classificados.
""",
        "observability/audit.md": """
# Auditoria

**Dono:** Governance + Security | **Status:** especificação | **Versão:** 0.1.1

Registrar quem solicitou, executou, revisou, aprovou, cancelou e alterou; versões
de contratos/workflows; transições; evidências; exceções; acessos e exportações.

- histórico append-only no Runtime futuro;
- timestamps confiáveis e IDs estáveis;
- integridade verificável e menor privilégio;
- segregação entre autor, revisor e aprovador;
- retenção e descarte por classificação;
- correção por evento compensatório, nunca alteração silenciosa.

Revisões procuram decisão sem autoridade, autoaprovação, versão deprecada, gate
sem evidência, acesso fora do escopo e quebra de sequência.
""",
        "observability/status-model.md": """
# Modelo de Status

**Dono:** Orchestrator | **Status:** especificação | **Versão:** 0.1.1

`planned` não satisfaz precondições; `ready` pode iniciar; `running` executa;
`awaiting_approval` espera autoridade; `blocked` espera dependência; `failed`
terminou com falha; `completed` concluiu critérios; `cancelled` foi encerrado.

Transições: `planned → ready|cancelled`; `ready → running|cancelled`;
`running → awaiting_approval|blocked|failed|completed|cancelled`;
`awaiting_approval → running|blocked|completed|cancelled`;
`blocked → ready|cancelled`; `failed → ready|cancelled` por nova tentativa.

Toda transição registra estado anterior/novo, ator, autoridade, motivo, timestamp,
trace e evidência. Estados terminais não são reabertos.
""",
        "planning/RELEASES.md": """
# Releases

**Dono:** Product Manager | **Status:** planejado | **Versão:** 0.1.1

| Release | Entrada | Critério de saída | Aprovação |
|---|---|---|---|
| 0.1 Fundação | visão | auditoria documental sem bloqueador | Product + Quality |
| 0.2 Registry/contratos | 0.1 aceita | schemas e compatibilidade | Tech + Quality |
| 0.3 Workflows | 0.2 aceita | cenários declarativos validados | Product + Delivery |
| 0.4 Orchestrator | ADRs/autorização | estados e aprovações testados | Tech + Security |
| 0.5 Runtime | 0.4 estável | lifecycle e isolamento testados | Tech + Quality |
| 0.6 Piloto | responsáveis nomeados | métricas e retrospectiva | Sponsor |
| 1.0 Utilizável | piloto aceito | release, handover e suporte | Sponsor + Product |

Todas seguem SemVer, changelog, compatibilidade, migração e rollback. Releases
0.4 em diante não estão autorizadas por esta entrega.
""",
        "planning/DEPENDENCIES.md": """
# Dependências

**Dono:** Delivery Lead | **Status:** ativo | **Versão:** 0.1.1

| Dependência | Necessária para | Dono | Condição |
|---|---|---|---|
| autoridades nomeadas | aprovações materiais | Executive | papéis registrados |
| schemas declarativos | release 0.2 | Tech Lead | ADR e testes |
| identidade/autorização | Runtime | Security | threat model aprovado |
| persistência/concorrência | Orchestrator | Tech Lead | ADR aceito |
| isolamento de contexto | Runtime | Security/Privacy | controles testáveis |
| orçamento e ambiente | piloto | Sponsor | autorização |
| primeiro incremento | piloto | Product Manager | brief aprovado |

Dependência bloqueada registra impacto, responsável e gatilho de retomada.
Nenhuma escolha tecnológica é presumida.
""",
    }
    for path, content in documents.items():
        write(path, content)


def clarify_legacy_documents() -> None:
    legacy = {
        "templates/project-brief.md": "templates/business/project-brief.md",
        "templates/handoff.md": "templates/documentation/handover.md",
        "templates/architecture-adr.md": "templates/architecture/architecture-document.md e templates/architecture/adr.md",
        "templates/roadmap-risk.md": "templates/planning/technical-roadmap.md e templates/planning/risks.md",
        "templates/quality-release.md": "templates/testing/test-report.md e templates/deployment/deployment-plan.md",
        "templates/retrospective-postmortem.md": "templates/operations/retrospective.md e templates/operations/incident-report.md",
    }
    for path, canonical in legacy.items():
        original = (ROOT / path).read_text(encoding="utf-8")
        if "Compatibilidade histórica" not in original:
            write(
                path,
                f"""
> **Compatibilidade histórica:** este modelo agregado foi preservado para
> projetos existentes. Novos projetos devem usar `{canonical}`. Não mantenha
> cópias canônicas nos dois formatos.

{original}
""",
            )

    workflow_legacy = {
        "workflows/intake-discovery.md": "project-intake.md e discovery.md",
        "workflows/definition-planning.md": "business-analysis.md, architecture.md e planning.md",
        "workflows/delivery-quality.md": "implementation.md, code-review.md e testing.md",
        "workflows/release-operations.md": "deployment.md, handover.md e maintenance.md",
        "workflows/change-control.md": "change-request.md",
    }
    for path, canonical in workflow_legacy.items():
        original = (ROOT / path).read_text(encoding="utf-8")
        if "Workflow agregado legado" not in original:
            write(
                path,
                f"""
> **Workflow agregado legado:** preservado para rastrear projetos anteriores.
> Novas execuções usam `{canonical}` e os YAML registrados. Em conflito,
> prevalecem os componentes registrados.

{original}
""",
            )


def specialize_pilot_readmes() -> None:
    purposes = {
        "business-analysis": "Registrar perguntas, requisitos provisórios, regras e escopo somente após validação de fonte.",
        "architecture": "Registrar opções e ADRs propostos; nenhuma stack está aprovada.",
        "planning": "Planejar validação e piloto sem autorizar implementação de produção.",
        "decisions": "Guardar decisões humanas e ADRs com status; perguntas não são decisões.",
        "logs": "Guardar eventos sintéticos ou da execução documental, sem dados pessoais ou segredos.",
        "reports": "Guardar auditorias, métricas do piloto e recomendações para gates.",
    }
    for folder, purpose in purposes.items():
        write(
            f"projects/asep-self-development/{folder}/README.md",
            f"""
# ASEP Self-development — {folder}

## Finalidade

{purpose}

## Condição de uso

Cada novo artefato identifica fonte, dono, status e relação com o workflow
`software-project`. Itens sem confirmação permanecem como pergunta ou hipótese.

## Limite atual

Esta pasta não autoriza código de produção, gasto, publicação, escolha de stack
ou uso de dados reais. Essas ações dependem das decisões em
[`reports/open-decisions.md`](../../../reports/open-decisions.md).
""",
        )


AGENT_DETAILS = {
    "orchestrator": ("classificação, roteamento, grafos de dependência, gates, segregação de funções e gestão de estado", "classificar a demanda; fixar workflow/versões; decompor tarefas; validar dependências; controlar gates e aprovações; consolidar e encerrar", "roteamento compatível, nenhum gate sem evidência, bloqueios com dono e encerramento auditável"),
    "business-analyst": ("elicitação, processos, stakeholders, requisitos, regras, MVP, MoSCoW e critérios de aceite", "mapear fontes e stakeholders; entender processo atual; separar problema de solução; catalogar requisitos/regras; validar escopo e aceite", "requisitos singulares e testáveis, origem explícita, conflitos visíveis e validação do decisor"),
    "software-architect": ("atributos de qualidade, modelagem de sistemas, integração, dados, resiliência, segurança, custo e ADR", "validar requisitos; identificar drivers; modelar contexto/fronteiras; comparar alternativas; tratar falhas e operação; registrar ADRs", "trade-offs explícitos, decisões rastreáveis, riscos operacionais tratados e estratégia de saída"),
    "project-manager": ("planejamento adaptativo, estimativa, dependências, RAID, capacidade, caminho crítico e comunicação", "validar escopo; fatiar entregas; estimar por faixas; mapear dependências/capacidade; manter riscos e replanejar por gatilhos", "plano executável, compromissos com premissas, dependências com dono e status baseado em evidência"),
    "ux-ui-designer": ("pesquisa, arquitetura da informação, interaction design, conteúdo, design systems e acessibilidade", "validar usuários/evidências; mapear jornadas e estados; explorar alternativas; especificar interação/conteúdo; testar acessibilidade e entendimento", "jornadas completas, estados/erros cobertos, rastreabilidade a requisitos e evidência de acessibilidade"),
    "database-engineer": ("modelagem, integridade, transações, índices, migração, retenção, backup, restauração e capacidade", "validar ownership/acessos; modelar entidades/relações; definir integridade e índices; planejar migração/rollback; testar recuperação", "integridade verificável, consultas críticas justificadas, migração reversível e restauração exercitada"),
    "backend-engineer": ("domínio, APIs, integração, concorrência, idempotência, segurança, testes e observabilidade", "refinar contrato; implementar regra e fronteiras; tratar erros/timeouts; instrumentar; testar unidade/integração/contrato; preparar review", "comportamento conforme contrato, autorização no servidor, falhas controladas e testes reproduzíveis"),
    "frontend-engineer": ("HTML semântico, acessibilidade, estado, performance, segurança do cliente, testes e observabilidade web", "validar design/contratos; implementar estados e navegação; integrar API; tratar erro/permissão; testar acessibilidade e jornadas", "semântica e teclado corretos, estados completos, orçamento de performance e compatibilidade validada"),
    "mobile-engineer": ("lifecycle móvel, conectividade, permissões, armazenamento seguro, acessibilidade, performance e release stores", "validar plataformas; implementar estados online/offline; tratar permissões/lifecycle; testar dispositivos; preparar rollout e telemetria", "recuperação de conectividade, permissões mínimas, dispositivos representativos e política de loja atendida"),
    "ai-engineer": ("modelos, prompting, RAG, dados, avaliação, segurança, incerteza, custo, drift e supervisão humana", "definir tarefa/limites; validar dados; escolher baseline; criar conjunto de avaliação; testar qualidade/abuso; documentar fallback e monitoramento", "evaluation plan reproduzível, versões fixadas, incerteza comunicada, fallback seguro e model card"),
    "qa-engineer": ("estratégia orientada a risco, níveis de teste, dados, ambientes, automação, defeitos e release", "mapear riscos/requisitos; selecionar técnicas; preparar dados/ambiente; executar e registrar; classificar defeitos; recomendar release", "matriz risco–teste, execução reproduzível, defeitos com severidade e risco residual explícito"),
    "security-engineer": ("threat modeling, identidade, autorização, criptografia, secrets, supply chain, privacidade e incidentes", "classificar ativos/dados; modelar atores/fronteiras/abuso; especificar controles; verificar implementação; priorizar achados; registrar risco", "ameaças relevantes cobertas, controles verificados, achados rastreáveis e aceite de risco por autoridade"),
    "devops-engineer": ("CI/CD, infraestrutura, ambientes, secrets, rollout, SLO, observabilidade, backup, rollback e custo", "validar release; preparar ambiente/pipeline; ensaiar migração/rollback; configurar sinais; executar rollout aprovado; observar e comunicar", "ambiente reproduzível, rollback testado, alertas acionáveis, go/no-go registrado e runbook utilizável"),
    "documentation-engineer": ("arquitetura da informação, docs-as-code, escrita técnica, conteúdo de produto, acessibilidade e localização", "identificar públicos/tarefas; inventariar fontes; estruturar conteúdo; validar precisão; testar navegação; versionar e publicar com aprovação", "conteúdo correto e localizável, exemplos verificados, links válidos e aceite do público responsável"),
    "support-engineer": ("triagem, diagnóstico, incidentes, SLO, comunicação, problem management, manutenção e conhecimento", "classificar impacto; preservar evidência; usar runbook; conter/escalar; comunicar; registrar causa; propor correção e aprendizado", "restauração segura, timeline verificável, comunicação adequada e ação preventiva com dono"),
}


def rewrite_agent_manuals() -> None:
    for agent_id, spec in AGENTS.items():
        contract = yaml.safe_load(
            (ROOT / "contracts" / f"{agent_id}.yaml").read_text(encoding="utf-8")
        )
        name = contract["name"]
        detail = AGENT_DETAILS[agent_id]
        outputs = ", ".join(contract["required_outputs"])
        inputs = ", ".join(contract["required_inputs"])
        next_agents = ", ".join(contract["next_agents"]) or "Orchestrator para encerramento"
        cannot = "; ".join(contract["cannot"])
        write(
            f"agents/{agent_id}.md",
            f"""
# Agente: {name}

**Versão:** 0.1.1 | **Status:** ativo | **Dono:** {contract["department"]}

## 1. Identidade
Especialista ASEP responsável pelo domínio de {contract["department"]}, orientado por evidências e pelo contrato versionado.
## 2. Cargo
{name}.
## 3. Departamento
`{contract["department"]}`.
## 4. Missão
{contract["mission"].capitalize()}.
## 5. Objetivo
Produzir `{outputs}` compatíveis com o próximo contrato e suficientes para os gates atribuídos.
## 6. Papel
Aplicar julgamento especializado, tornar trade-offs explícitos e colaborar sem assumir autoridade de outro domínio.
## 7. Autoridade
Decidir escolhas reversíveis do próprio domínio dentro de standards aprovados; recomendar decisões materiais ao responsável humano.
## 8. Responsabilidades
{detail[1].capitalize()}; manter decisões, riscos, evidências e handoff.
## 9. O que não faz
{cannot}.
## 10. Conhecimentos necessários
{detail[0].capitalize()}, além do lifecycle, contratos, rastreabilidade e classificação de dados da ASEP.
## 11. Fontes obrigatórias de consulta
[`AGENTS.md`](../AGENTS.md), [`core/SYSTEM.md`](../core/SYSTEM.md), [`contracts/{agent_id}.yaml`](../contracts/{agent_id}.yaml), workflow fixado, artefatos do projeto, knowledge e standards do domínio.
## 12. Entradas
Obrigatórias: `{inputs}`. Opcionais: constraints, decisions e risk-register, conforme o contrato.
## 13. Validação das entradas
Confirmar ID, produtor, versão, status, autorização, classificação, integridade e compatibilidade semântica; lacuna crítica bloqueia.
## 14. Processo de execução
Após o lifecycle comum: {detail[1]}. Cada decisão referencia a entrada e cada achado informa impacto e dono.
## 15. Entregáveis
`{outputs}`, com os nomes canônicos do contrato.
## 16. Estrutura dos artefatos
ID, versão, status, dono, objetivo, fontes, fatos/hipóteses, conteúdo do domínio, alternativas, decisões, riscos, evidências, pendências e handoff.
## 17. Critérios de qualidade
{detail[2].capitalize()}; outputs compatíveis com `{next_agents}` e gate avaliado por evidência.
## 18. Checklist de autoavaliação
- [ ] Entradas, autoridade e classificação foram validadas.
- [ ] Fatos, hipóteses, decisões e perguntas estão separados.
- [ ] O procedimento e os standards específicos do domínio foram aplicados.
- [ ] Entregáveis usam nomes canônicos e possuem evidências.
- [ ] Limites de outros agentes foram respeitados.
- [ ] Handoff informa riscos, pendências, responsável e gatilho.
## 19. Comunicação
Seguir [`core/COMMUNICATION.md`](../core/COMMUNICATION.md); comunicar bloqueio cedo e registrar decisões duráveis fora de conversas efêmeras.
## 20. Passagem para o próximo agente
Entregar a `{next_agents}` os outputs versionados, validações, risco residual, decisões e lacunas; o receptor confirma required inputs.
## 21. Quando interromper
Entrada crítica ausente ou contraditória, origem não confiável, autorização insuficiente ou conclusão não sustentada por evidência.
## 22. Quando escalar
Risco alto, incidente, conflito de autoridade, dependência sem dono, mudança material ou gate bloqueado.
## 23. Quando pedir decisão humana
Produção, gasto, acesso restrito, exceção, aceite material, decisão difícil de reverter ou risco residual alto.
## 24. Erros proibidos
Inventar fatos/requisitos/testes/aprovações; ocultar incerteza; exceder o contrato; expor dados; aprovar o próprio conflito; apagar histórico.
## 25. Critérios de conclusão
Todos os required outputs existem, critérios específicos foram verificados, gate e decisões estão registrados e o handoff foi aceito.
## 26. Exemplo de execução
Recebe `{inputs}`; valida versões e fontes; aplica {detail[1]}; produz `{outputs}`; faz self-review; anexa evidências; encaminha a `{next_agents}` ou bloqueia com decisão estruturada.
## 27. Prompt operacional
> Você é {name}. {contract["mission"].capitalize()}. Carregue contrato, contexto, knowledge e standards; valide `{inputs}`; não invente; aplique {detail[1]}; produza `{outputs}`; revise contra {detail[2]}; gere evidência e handoff. Interrompa diante de lacuna crítica, autoridade insuficiente ou risco alto.
""",
        )


DEPARTMENT_DETAILS = {
    "executive": ("direção, sustentabilidade e limites de risco", "estratégia, portfólio, orçamento, políticas e conflitos de autoridade", "decisões estratégicas, apetite de risco e prioridades", "resultado do portfólio, exposição e decisões vencidas"),
    "business": ("valor, problema e regras de negócio", "discovery, stakeholders, requisitos, escopo, prioridade e aceite", "briefs, requisitos, regras e decisões de produto", "requisitos reabertos, aceite e resultado"),
    "architecture": ("coerência e evolução técnica", "drivers, fronteiras, integrações, dados, atributos de qualidade e ADRs", "arquitetura, ADRs e restrições técnicas", "decisões sem ADR, acoplamento e risco técnico"),
    "product-design": ("experiência útil, compreensível e acessível", "pesquisa, jornadas, interação, conteúdo, interface e acessibilidade", "flows, especificações e evidências de validação", "problemas de usabilidade, acessibilidade e retrabalho"),
    "engineering": ("implementação sustentável", "código, integração, revisão, testes de componente e dívida técnica", "incrementos e evidências de implementação", "falhas, retrabalho, lead time e dívida"),
    "data": ("integridade, disponibilidade e governança de dados", "modelagem, ownership, qualidade, migração, retenção e recuperação", "modelos, planos de migração e evidência de integridade", "incidentes de dados, restauração e qualidade"),
    "quality": ("cobertura verificável de riscos", "estratégia, testes, ambientes, defeitos, gates e recomendação de release", "planos, relatórios e avaliação de risco residual", "defeitos escapados, flakiness e cobertura de risco"),
    "security": ("proteção de ativos e pessoas", "threat modeling, controles, privacidade, findings, incidentes e risco residual", "threat models, revisões e achados", "tempo de correção, recorrência e exposição"),
    "operations": ("entrega previsível e serviço confiável", "coordenação, CI/CD, ambientes, SLO, observabilidade, incidentes e suporte", "planos, runbooks, releases e relatórios operacionais", "disponibilidade, MTTR, change failure e bloqueios"),
    "documentation": ("informação correta e transferível", "arquitetura da informação, guias, referência, handover e governança editorial", "documentação revisada e handovers", "encontrabilidade, links, atualização e sucesso do leitor"),
}


def rewrite_departments() -> None:
    for department_id, detail in DEPARTMENT_DETAILS.items():
        write(
            f"departments/{department_id}.md",
            f"""
# Departamento: {department_id}

**Versão:** 0.1.1 | **Status:** ativo | **Dono:** Executive

## Missão
Responder por {detail[0]} na ASEP.
## Responsabilidades
Manter competências, capacidade, standards e revisão relativos a {detail[1]}.
## Limites
Não altera unilateralmente prioridade, contrato, orçamento ou autoridade de outro departamento.
## Autoridade
Aprova decisões reversíveis do domínio e pode bloquear entrega que viole gate sob sua responsabilidade.
## Entradas
Demandas, riscos, artefatos predecessores, achados, métricas e exceções propostas.
## Saídas
{detail[2].capitalize()}, decisões de domínio, evidências e handoffs.
## Relacionamentos
Coordena pelo Orchestrator; consulta Product, Architecture, Quality, Security e Operations conforme impacto.
## Indicadores de qualidade
{detail[3].capitalize()}, além de handoffs rejeitados e ações vencidas.
## Aprovação humana
Obrigatória para política, produção, gasto, dado restrito, exceção material e risco alto.
""",
        )


ROLE_DOMAIN = {
    "executive": ("estratégia, portfólio e apetite de risco", "prioridades, políticas, orçamento e conflitos executivos"),
    "orchestrator": ("coordenação do sistema", "classificação, roteamento, gates, bloqueios e consolidação"),
    "business-analysis": ("entendimento de negócio", "stakeholders, processos, requisitos, regras e critérios"),
    "architecture": ("coerência técnica", "drivers, alternativas, fronteiras, ADRs e risco técnico"),
    "project-management": ("entrega previsível", "planejamento, capacidade, dependências, riscos e status"),
    "product-design": ("experiência acessível", "pesquisa, jornadas, interação, conteúdo e validação"),
    "database-engineering": ("dados íntegros e recuperáveis", "modelagem, integridade, migração, retenção e recuperação"),
    "backend-engineering": ("serviços confiáveis", "domínio, APIs, integrações, segurança e observabilidade"),
    "frontend-engineering": ("experiências web", "semântica, estados, acessibilidade, performance e integração"),
    "mobile-engineering": ("experiências móveis", "lifecycle, conectividade, permissões, dispositivos e release"),
    "ai-engineering": ("componentes de IA avaliáveis", "dados, avaliação, incerteza, segurança, custo e fallback"),
    "quality-assurance": ("evidência de qualidade", "riscos, estratégia de teste, defeitos e release"),
    "security-engineering": ("segurança e privacidade", "ameaças, controles, achados e risco residual"),
    "devops-engineering": ("entrega e confiabilidade", "pipeline, ambiente, rollout, SLO, rollback e runbook"),
    "documentation-engineering": ("informação utilizável", "conteúdo, estrutura, precisão, navegação e handover"),
    "support-maintenance": ("continuidade do serviço", "triagem, incidente, diagnóstico, manutenção e aprendizado"),
}


def rewrite_roles() -> None:
    for role_id, detail in ROLE_DOMAIN.items():
        write(
            f"roles/{role_id}.md",
            f"""
# Papel: {role_id}

**Versão:** 0.1.1 | **Status:** ativo | **Dono:** departamento correspondente

## Missão
Garantir {detail[0]} com responsabilidade e evidência.
## Responsabilidades
Responder por {detail[1]}; manter riscos, decisões e artefatos do domínio.
## Limites
Não assume prioridade, aceite, orçamento ou decisão técnica/risco de outro papel.
## Autoridade
Decide itens reversíveis do domínio e recomenda decisões materiais ao accountable definido em `core/ORGANIZATION.md`.
## Entradas
Objetivo, contexto autorizado, artefatos predecessores, restrições, critérios e riscos.
## Saídas
Recomendação ou decisão de domínio, artefatos verificáveis, evidências de gate e handoff.
## Relacionamentos
Coordena com Orchestrator e consulta especialistas afetados; conflito vai ao dono da decisão.
## Indicadores
Decisões rastreáveis, gates com evidência, achados resolvidos e handoffs compatíveis.
## Aprovação humana
Produção, gasto, escopo material, dado restrito, exceção, irreversibilidade ou risco alto.
""",
        )


KNOWLEDGE_GUIDANCE = {
    "requirements": ["Use um ID estável e uma única necessidade por requisito", "ligue origem, regra, prioridade e critérios", "trate alteração por versão e change request"],
    "stakeholders": ["Separe sponsor, decisor, operador, usuário e afetado", "registre influência e informação que cada grupo confirma", "minimize dados pessoais no mapa"],
    "personas": ["Crie somente com pesquisa suficiente", "descreva objetivos, tarefas e contexto em vez de estereótipos", "marque perfil provisório como hipótese"],
    "user-stories": ["Use story para conversa sobre valor, não como especificação completa", "inclua critérios, regras e dependências", "divida por resultado observável"],
    "use-cases": ["Defina ator, gatilho, precondição e resultado", "cubra fluxo principal, alternativos e exceções", "relacione regras e requisitos não funcionais"],
    "business-rules": ["Declare uma regra por ID e fonte autorizada", "registre condições, exceções, precedência e vigência", "não confunda política com implementação"],
    "mvp": ["Escolha o menor conjunto coerente que testa valor", "preserve obrigações e operação essencial", "registre explicitamente o que fica fora"],
    "prioritization": ["Considere valor, risco, custo de atraso e dependência", "registre justificativa e autoridade", "revise quando evidência ou capacidade mudar"],
    "principles": ["Faça fronteiras refletirem responsabilidade e mudança", "minimize acoplamento e maximize coesão", "projete observabilidade e recuperação desde o início"],
    "architecture-selection": ["Derive opções dos atributos de qualidade", "compare custo total, risco, equipe e reversibilidade", "use PoC apenas para incerteza relevante"],
    "modular-monolith": ["Defina módulos com ownership e APIs internas", "impeça acesso cruzado direto a dados", "extraia serviços somente por pressão comprovada"],
    "microservices": ["Exija autonomia de domínio e implantação como benefício", "inclua rede, consistência, observabilidade e operação no custo", "evite banco compartilhado sem ownership explícito"],
    "clean-architecture": ["Mantenha regras de domínio independentes de detalhes", "use portas onde há fronteira real de mudança", "evite camadas cerimoniais sem benefício"],
    "ddd": ["Construa linguagem ubíqua com especialistas", "delimite bounded contexts e relações", "aplique modelagem tática apenas onde a complexidade justificar"],
    "api-design": ["Modele contrato pelo consumidor e pela semântica", "defina erros, idempotência e compatibilidade", "trate autorização, limites e depreciação"],
    "event-driven": ["Evento registra fato passado e produtor responsável", "defina entrega, ordem, duplicidade e evolução de schema", "projete replay, DLQ e recuperação sem presumir exactly-once"],
    "scalability": ["Comece por carga e SLO medidos", "identifique gargalo antes de distribuir", "compare escala vertical, horizontal, cache e particionamento"],
    "resilience": ["Defina orçamento de timeout por jornada", "retry somente em falha transitória e operação segura", "teste degradação, circuit breaker e recuperação"],
    "estimation": ["Use faixa e confiança, não precisão falsa", "explicite escopo, premissas e dependências", "reestime quando o aprendizado mudar a distribuição"],
    "backlog": ["Ordene por resultado e não por volume", "mantenha itens prontos com critérios e dependências", "remova ou revalide itens envelhecidos"],
    "risk-management": ["Formule risco como evento e impacto", "justifique probabilidade e severidade", "atribua resposta, dono e gatilho"],
    "dependencies": ["Diferencie dependência técnica, decisória e externa", "registre dono, data e impacto", "defina alternativa ou condição de bloqueio"],
    "delivery-planning": ["Planeje incrementos demonstráveis", "respeite capacidade e trabalho de qualidade", "defina caminho crítico e gatilhos de mudança"],
    "test-strategy": ["Parta de riscos e critérios", "defina níveis, ambientes, dados e responsabilidades", "registre entrada, saída e risco residual"],
    "test-pyramid": ["Mantenha maior volume de testes rápidos e determinísticos", "use integração nas fronteiras", "reserve E2E para jornadas críticas"],
    "acceptance-testing": ["Transforme critérios em resultados observáveis", "inclua regras e exceções críticas", "obtenha aceite do responsável de produto"],
    "regression": ["Selecione por impacto da mudança e histórico", "mantenha baseline confiável", "investigue flakiness em vez de repetir até passar"],
    "automation": ["Automatize feedback repetível e valioso", "controle dados, relógio e dependências", "meça manutenção e tempo de diagnóstico"],
    "secure-development": ["Inclua segurança em discovery, design, implementação e operação", "automatize controles repetíveis", "bloqueie achado crítico sem mitigação"],
    "threat-modeling": ["Identifique ativos, atores e trust boundaries", "modele abuso e impacto", "ligue mitigação, verificação e risco residual"],
    "authentication": ["Proteja inscrição, login, sessão e recuperação", "aplique MFA conforme risco", "não revele existência de conta indevidamente"],
    "authorization": ["Valide no servidor e negue por padrão", "modele recurso, ação, sujeito e contexto", "teste isolamento horizontal e vertical"],
    "secrets": ["Use cofre e credenciais de curta duração", "limite escopo e registre rotação", "trate exposição como incidente"],
    "privacy": ["Defina finalidade e base autorizada", "minimize coleta, acesso e retenção", "permita direitos, descarte e auditoria"],
}


def enrich_knowledge() -> None:
    for path in (ROOT / "knowledge").rglob("*.md"):
        if path.name == "README.md" or path.stem == "fundamentals":
            continue
        guidance = KNOWLEDGE_GUIDANCE.get(path.stem)
        if not guidance:
            continue
        current = path.read_text(encoding="utf-8")
        objective_match = __import__("re").search(
            r"## Objetivo\n(.*?)(?=\n## )", current, __import__("re").S
        )
        objective = (
            objective_match.group(1).strip()
            if objective_match
            else f"Orientar decisões sobre {path.stem}."
        )
        bullets = "\n".join(f"- {item}." for item in guidance)
        write(
            str(path.relative_to(ROOT)),
            f"""
# {path.stem}

## Objetivo
{objective}

## Conceitos e limites

Este tema orienta julgamento; não substitui requisitos confirmados, decisão do
dono nem o standard aplicável. Termos e estado devem ser definidos no contexto
do projeto.

## Aplicação operacional

{bullets}

## Critérios de decisão

Compare resultado esperado, evidência, risco, restrições, custo total, capacidade,
reversibilidade e impacto operacional. Registre alternativas quando a escolha for
material.

## Erros comuns

- copiar uma solução sem verificar contexto;
- transformar hipótese em fato ou preferência em restrição;
- omitir exceções, ownership, falha ou estratégia de saída;
- produzir artefato sem ligação a requisito, decisão ou gate.

## Checklist

- [ ] Conceitos e fonte estão claros.
- [ ] As três orientações operacionais foram tratadas.
- [ ] Alternativas, exceções e riscos relevantes estão registrados.
- [ ] A decisão aponta para agente, workflow, standard e evidência.

## Relação com agentes e workflows

O especialista do domínio aplica o conteúdo; Business Analyst preserva a origem;
Architect avalia impacto sistêmico; QA transforma risco em validação. Consulte nas
fases de discovery, definição, execução e review quando aplicável.

## Referências internas

[`core/QUALITY.md`](../../core/QUALITY.md), standards e playbook do domínio,
além do contrato do agente responsável.
""",
        )


def main() -> None:
    normalize_contracts()
    rewrite_standards()
    rewrite_runtime()
    rewrite_workflows()
    rewrite_templates()
    update_workflow_registry()
    improve_folder_purpose()
    rewrite_observability_and_planning()
    clarify_legacy_documents()
    specialize_pilot_readmes()
    rewrite_agent_manuals()
    rewrite_departments()
    rewrite_roles()
    enrich_knowledge()
    print("Correções documentais aplicadas.")


if __name__ == "__main__":
    main()
