# Orchestrator — classification

## Finalidade
Especificar tipo de projeto, risco, dados, complexidade e urgência.
## Regras
Consultar Registry; fixar versões; validar dependências; não criar requisitos nem substituir especialista; manter segregação de funções; registrar eventos e decisões; bloquear sem evidência.
## Entradas e saídas
Recebe projeto, contexto autorizado e estado. Produz tarefas, roteamento, solicitações de aprovação, eventos, consolidação e handoff.
## Falhas
Preservar contexto, registrar causa, tentar apenas ação segura/idempotente e escalar com opções.
## Implementação futura
TODO(Runtime Owner): definir schema persistente, controle de concorrência, identidade e APIs após ADR e aprovação humana.
