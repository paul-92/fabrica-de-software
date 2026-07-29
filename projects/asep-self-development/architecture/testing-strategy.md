# Testing Strategy

**ID:** ARCH-TST-001 | **Versão:** 0.1.0 | **Status:** approved

## Princípio

pytest, testes determinísticos, filesystem temporário e cobertura orientada aos
riscos R-003/R-004/R-005/R-009. Percentual de cobertura não substitui cenários.

## Níveis

| Nível | Alvo | Exemplos |
|---|---|---|
| unit | domínio puro | transições, grafo, gate, erro, path policy |
| contract | portas e schemas | Registry, Contract, Workflow, AgentPort |
| integration | adaptadores locais | YAML, atomic write, audit JSONL, Jinja2 |
| CLI | interface | help, códigos, confirmação, saída JSON |
| end-to-end | fluxo MVP | init→run→approval→resume→complete/cancel |
| recovery | falhas | crash, linha truncada, lock, retry |
| security | abuso | path traversal, unsafe YAML, secret redaction |

## Test doubles

Clock, IdGenerator, AgentPort e repositories em memória. Golden files apenas para
Markdown estável; normalizar timestamps/IDs. Não mockar o domínio que está sendo
testado.

## Quality gates

Cada FR/NFR Must liga a pelo menos um teste de aceitação. ADRs possuem testes de
consequência: ordem sequencial, estado atômico, version pinning, gate sem evidência,
aprovação, cancelamento e ausência de rede.

## Fora do escopo

Teste de carga sem cenário/target, browser, banco, container e provedor de IA.
