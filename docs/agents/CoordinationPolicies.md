# Coordination Policies

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** contrato ativo

`CoordinationPolicy` é imutável e define:

- máximo de agentes e assignments;
- ordem por dependências/prioridade ou ordem do plano;
- timeout lógico encaminhado ao Runtime, sem interrupção própria;
- interrupção após falha;
- fallback de seleção;
- `AgentSelectionPolicy`.

`AgentSelectionPolicy` controla preferência por agente explícito, afinidade por
capability e indisponibilidade declarada. A resolução é estável:

1. agente explícito elegível;
2. afinidade configurada elegível;
3. primeiro agente elegível na ordenação determinística do Registry.

Capabilities não registradas ou agentes indisponíveis causam
`CapabilityResolutionError`. Não há scoring probabilístico nem consulta a LLM.

Paralelismo futuro poderá substituir a implementação da fila preservando
`AgentAssignment`, `CoordinationContext`, `CoordinationResult` e as portas
públicas.
