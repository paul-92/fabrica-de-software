# Fase 16 — Software Generation & Validation Pipeline

**Dono:** Engenharia ASEP
**Versão:** 1.0
**Status:** concluída e comprovada por implementação e testes

## Objetivo

Materializar conteúdo determinístico definido no plano em um workspace e
validá-lo com pytest, preservando as fronteiras de Agent, Tool, Planning,
Coordination, artefatos e Quality Gates.

## 16.1 — Reutilização

A implementação reutiliza `Agent`, `DeveloperAgent`, `ToolRequest`,
`ToolExecutionService`, resolução segura de workspace, `ExecutionPlan`,
`PlanStep`, Coordinator, `ArtifactManager` e `QualityGateEngine`. Não existe
um gerador paralelo nem acesso direto do Agent ao filesystem.

## 16.2 — Safe WriteFileTool

`WriteFileTool` declara `ToolMetadata` com id `write-file` e capability
`write_file`. Seu payload exige `content: str`, aceita `path` relativo e
`overwrite: bool` (padrão falso). A Tool chama `resolve_workspace_path`, cria
diretórios pais, escreve UTF-8 e retorna path, bytes UTF-8 e indicador de
overwrite.

A política central rejeita caminhos absolutos, traversal e escapes por
symlink; bloqueia `.git`, `.ssh`, `.env`, `.env.*`, `.netrc` e nomes de
credenciais; e mantém o alvo no workspace. Alvo existente exige
`overwrite=True`; diretório no lugar de arquivo e falha de escrita produzem
erro estruturado.

## 16.3–16.5 — DeveloperAgent, múltiplos arquivos e alteração

```text
DeveloperAgent -> ToolRequest -> ToolExecutionService
               -> WriteFileTool -> workspace
```

O Agent suporta `write_file`. Configurações da etapa chegam em
`PlanStep.metadata`; etapas distintas podem indicar paths e conteúdos
distintos no mesmo workspace. Arquivo novo usa o padrão sem overwrite. A
alteração é deliberada: pode haver leitura por `ReadFileTool` numa etapa e a
escrita posterior só substitui o alvo quando `overwrite=True`. Isso não é
geração autônoma: conteúdo e ação são determinados pelo plano.

## 16.6 — Resultados entre etapas

Antes de cada execução, o Coordinator inclui em
`AgentExecutionRequest.input["previous_results"]` os resultados já obtidos,
em ordem. O contrato existente é reutilizado. A solicitação também transporta
o `PlanStep` serializado. O `DeveloperAgent` combina
`request.metadata["options"]`, quando fornecido pelo contexto, com a metadata
do step contida nessa entrada; valores da etapa prevalecem. Isso permite
configuração específica sem novo DTO.

## 16.7 — Validação automática

`RunTestsTool` declara id `run-tests` e capability `test`. Recebe `paths`
(padrão `tests`), resolve cada caminho dentro do workspace e executa
`sys.executable -m pytest ...` com o workspace como working directory. O
timeout vem do request ou usa 300 segundos. A saída contém `exit_code`,
`stdout`, `stderr` e `command`; zero gera `SUCCEEDED`, outro código gera
`FAILED`/`tests_failed`. `DeveloperAgent` suporta `test` e monta o payload a
partir de `test_paths`.

## 16.8 — Gate de geração

```text
RunTestsTool -> ToolExecutionStatus -> DeveloperAgent -> AgentResult
             -> QualityGateEngine -> GateDecision
```

O gate não lê o exit code. A Tool transforma pytest reprovado em falha, o
DeveloperAgent a propaga em seu resultado, e o gate observa o contrato de
agente. `APPROVED` indica todos os critérios satisfeitos;
`APPROVED_WITH_PENDING`, critérios satisfeitos com warnings; `BLOCKED`, ao
menos um critério obrigatório não satisfeito. Um gate bloqueador prevalece no
`IntelligentExecutionResult`.

## 16.9 — E2E comprovado

```text
BusinessDescription -> ProjectBlueprint -> PlanningResult -> ExecutionPlan
 -> AgentCoordinator -> DeveloperAgent -> WriteFileTool -> filesystem
 -> RunTestsTool -> pytest -> ArtifactManager -> QualityGateEngine
 -> IntelligentExecutionResult
```

No caminho feliz, arquivos e testes são materializados, pytest passa, os
artefatos são persistidos e o resultado é `COMPLETED`. No caminho de falha,
pytest retorna erro, a falha percorre Tool/Agent, o gate bloqueia e o resultado
é `BLOCKED`; ela não é mascarada.

## Evidência automatizada

- `tests/test_tool_execution.py`: escrita UTF-8, pais, overwrite e contenção;
- `tests/qa/agents/coordination/test_end_to_end.py`: múltiplos arquivos,
  alteração, `previous_results` e geração/validação;
- `tests/qa/orchestrator/test_intelligent.py`: integração completa, artefatos,
  gates, caminho aprovado e bloqueado.

Implementação consolidada pelo commit `bd138b2`.

## Decisão relacionada

[ADR-031](../adr/ADR-031-controlled-software-generation.md).
