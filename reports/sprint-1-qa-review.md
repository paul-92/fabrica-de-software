# QA Review Independente — Sprint 1

**Projeto:** ASEP Self-development  
**Data:** 2026-07-28  
**Papel:** QA Lead e Revisor Técnico independente  
**Versão revisada:** 0.1.0  
**Quality Gate:** `QG-IMPLEMENT`  
**Resultado:** **APROVADA COM PENDÊNCIAS**

## Resumo executivo

O núcleo da Sprint 1 cumpre o critério operacional: `asep run
projects/asep-self-development` localiza o projeto, valida o manifesto, carrega o
Registry e o workflow, verifica consistência, inicializa o Orchestrator, registra
logs correlacionados e encerra sem executar agentes.

A revisão encontrou seis não conformidades corrigíveis dentro do escopo. Todas
foram corrigidas e protegidas por testes de regressão. A suíte final possui 16
testes aprovados; 36 YAML e os 7 workflows registrados foram validados.

Não há defeito crítico conhecido que impeça o uso local de preparação. Permanecem
quatro débitos delimitados para o backlog, principalmente a divergência entre a
estrutura física atual e as camadas do ADR-002. Por isso, a aprovação não é
incondicional.

## Itens revisados

- arquitetura aprovada e ADR-001–ADR-013;
- organização de `src/asep` e direção das dependências;
- CLI Typer e códigos de saída;
- Registry Loader e os seis catálogos requeridos;
- contratos individuais dos 15 agentes;
- Workflow Loader e os 7 workflows;
- Project Loader e manifesto do projeto piloto;
- Orchestrator de preparação;
- logging de console e JSONL;
- taxonomia e exposição segura de erros;
- modelos Pydantic;
- validação de paths e parsing YAML seguro;
- 16 testes automatizados;
- consistência entre implementação, Registry, contratos, workflows e decisões.

## Não conformidades

| ID | Severidade | Achado | Situação |
|---|---|---|---|
| NC-01 | alta | `StrictModel` aceitava campos desconhecidos, contrariando ADR-004/005 | corrigida |
| NC-02 | alta | arquivos individuais de contratos não eram validados nem reconciliados com agentes/gates | corrigida |
| NC-03 | alta | Registry e definição do workflow podiam divergir em etapas, agentes e gates | corrigida |
| NC-04 | média | logs não possuíam `run_id`, apesar da exigência de correlação | corrigida |
| NC-05 | média | mensagens Pydantic podiam repetir valores de entrada em terminal/log | corrigida |
| NC-06 | média | CLI retornava código `1`, divergindo da tabela aprovada de códigos | corrigida |
| NC-07 | média | artefatos e ADRs aprovados permaneciam com status `proposed` | corrigida |
| NC-08 | média | código está organizado por capacidade, não pelas camadas do ADR-002 | pendente |
| NC-09 | média | log diagnóstico e audit trail ainda compartilham o mesmo sink | pendente |
| NC-10 | baixa | `required_context` do workflow é carregado, mas sua suficiência semântica não é avaliada | pendente |
| NC-11 | baixa | não existe métrica confiável de cobertura por linha nem análise estática configurada | pendente |

## Correções realizadas

- modelos executáveis configurados com `extra="forbid"`;
- campos reais de agentes, workflows, projeto e estado modelados explicitamente;
- schema completo dos contratos de agentes adicionado;
- validação de contrato, versão, capacidades, consultas, próximos agentes e gates;
- verificação de owner dos quality gates e contratos sem agente;
- reconciliação entre catálogo e workflow para etapas, agentes e gates;
- regra estrutural por modo de etapa (`parallel`, `sequential`, `conditional`);
- `run_id` UUID incluído em todas as linhas JSONL;
- fechamento de handlers anteriores na reconfiguração do logger;
- erros de schema sanitizados, sem ecoar valores recebidos;
- categorias, próxima ação e códigos de saída alinhados ao desenho da CLI;
- status da Arquitetura e ADRs sincronizados com a aprovação humana já registrada;
- oito cenários de regressão adicionados.

Nenhuma funcionalidade de Sprint 2 foi implementada.

## Evidências

| Verificação | Resultado |
|---|---|
| pytest | 16 aprovados em 1,81 s |
| compilação/imports | aprovados |
| dependências instaladas | `pip check`: sem conflitos |
| YAML | 36 de 36 parseados com `safe_load` |
| workflows registrados | 7 de 7 carregados e validados |
| contratos | 15 de 15 carregados e validados pelo Registry |
| comando real | exit code `0`, fluxo preparado em aproximadamente 0,31 s |
| agentes executados | nenhum, conforme escopo |
| warnings esperados | 3 modos não executáveis sinalizados |
| cobertura por linha | não determinada com ferramenta confiável |

A tentativa de medir cobertura com `trace` da biblioteca padrão não foi aceita
como evidência percentual: a ferramenta reportou apenas linhas observadas e não
ofereceu o denominador adequado para o gate.

## Riscos

- uma futura expansão sem correção da estrutura pode aumentar acoplamento e custo
  de extração para ports/adapters;
- tratar log como auditoria pode induzir confiança indevida em imutabilidade,
  retenção e integridade ainda não implementadas;
- `required_context` incompleto pode ser descoberto somente em etapas futuras;
- ausência de cobertura mensurável reduz visibilidade sobre ramos de erro ainda
  não exercitados;
- o review especializado de Security continua necessário antes do respectivo gate.

## Débitos técnicos e backlog da Sprint 2

1. **DT-01 — ADR-002:** planejar migração incremental para
   `domain/application/ports/adapters/interfaces`, preservando a CLI.
2. **DT-02 — ADR-010:** separar log diagnóstico de audit trail append-only, com
   schema e política de falha.
3. **DT-03 — contexto:** transformar `required_context` em validações objetivas
   contra manifesto/artefatos.
4. **DT-04 — qualidade:** aprovar ferramenta e limiar de cobertura; adicionar
   verificação estática compatível com Python 3.12+.

Esses itens não autorizam início da Sprint 2; são somente recomendações para seu
backlog.

## Pendências humanas

- aprovar o tratamento do débito ADR-002 no planejamento da próxima Sprint;
- definir ferramenta e meta de cobertura;
- nomear responsáveis humanos por Quality e Security;
- manter a decisão de tailoring sequencial antes de qualquer executor.

## Recomendações

- não expandir o Orchestrator antes de resolver a direção arquitetural dos novos
  módulos;
- preservar os testes negativos de schema e referências como contract tests;
- manter mensagens sanitizadas e `run_id` obrigatório em novos eventos;
- exigir evidência separada quando audit trail for implementado;
- realizar Security Review antes do `QG-SECURITY`.

## Checklist completo

### Arquitetura

- [x] modular monolith e execução local preservados;
- [x] CLI não contém regra de workflow;
- [x] loaders e Orchestrator possuem responsabilidades identificáveis;
- [x] dependências podem ser injetadas no Orchestrator;
- [ ] estrutura física segue integralmente ADR-002;
- [x] não existem integrações ou infraestrutura fora do MVP.

### Código

- [x] nomes e funções são legíveis;
- [x] tipagem está presente nas interfaces principais;
- [x] não foi identificado código morto funcional;
- [x] não foram identificadas duplicações materiais;
- [x] imports revisados;
- [x] exceções genéricas removidas das fronteiras revisadas;
- [x] handlers de logging são fechados antes de reconfiguração.

### Registry e contratos

- [x] seis catálogos obrigatórios carregados;
- [x] IDs duplicados rejeitados;
- [x] paths fora da raiz rejeitados;
- [x] arquivos referenciados devem existir;
- [x] contratos individuais validados por schema;
- [x] agentes e contratos reconciliados;
- [x] owners, próximos agentes e gates reconciliados;
- [x] YAML inválido identifica o arquivo de origem.

### Workflow

- [x] YAML convertido em objetos Pydantic;
- [x] campos desconhecidos rejeitados;
- [x] etapas duplicadas rejeitadas;
- [x] dependências desconhecidas rejeitadas;
- [x] ciclos rejeitados;
- [x] agentes e gates validados;
- [x] catálogo e definição reconciliados;
- [x] modos fora da Sprint são sinalizados e não executados.

### CLI e erros

- [x] comando aprovado funciona;
- [x] diretório ausente retorna erro de uso;
- [x] validação retorna código `3`;
- [x] mensagem informa código estável e próxima ação;
- [x] traceback não é exibido em erros esperados;
- [x] valores de entrada não são repetidos por erros de schema.

### Logging e segurança

- [x] console e JSONL configurados;
- [x] timestamp UTC, nível, componente e evento presentes;
- [x] `run_id` presente;
- [x] leitura YAML usa `safe_load`;
- [x] paths do Registry ficam sob a raiz;
- [x] falha de preparação de log usa erro específico;
- [ ] audit trail é independente do log diagnóstico;
- [ ] política completa de redaction/retention implementada.

### Testes e documentação

- [x] Registry, Workflow, Project, CLI, Orchestrator e Logging testados;
- [x] cenários negativos de YAML, schema, path, contrato e ciclo cobertos;
- [x] execução real validada;
- [x] status dos ADRs sincronizado;
- [ ] cobertura por linha mensurada com ferramenta aprovada;
- [ ] análise estática dedicada configurada.

## Resultado final

**APROVADA COM PENDÊNCIAS.**

Justificativa: o fluxo de sucesso da Sprint 1 está funcional e as não
conformidades de correção imediata foram resolvidas com regressão automatizada.
Não há bloqueador crítico para a preparação local. A divergência do ADR-002, a
separação de auditoria, a validação semântica do contexto e a instrumentação de
qualidade devem permanecer visíveis e ser tratadas antes ou durante o próximo
incremento, mediante planejamento aprovado.

Esta decisão não autoriza o início da Sprint 2.
