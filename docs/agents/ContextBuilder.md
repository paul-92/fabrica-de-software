# ContextBuilder

**Público:** engenharia de agentes  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** implementado

## Objetivo

Construir o payload operacional entregue ao agente sem colocar recuperação,
retenção ou limite de tamanho dentro do Agent Runtime.

```text
Agent Runtime -> ContextProvider -> ContextBuilder -> MemoryService
```

## Comportamento

O builder:

1. solicita memórias não expiradas do agente;
2. ordena por importância, atualização e ID;
3. filtra metadata e contexto do workflow;
4. combina workflow, metadata e memórias;
5. inclui entradas enquanto respeita `max_context_size`;
6. indica truncamento;
7. registra `context_built` e duração.

O resultado é imutável e contém apenas valores JSON. O Runtime recebe somente
a porta `ContextProvider` e inclui o contexto em
`AgentRequest.inputs["memory_context"]`.

## Limitações

- tamanho é medido pela representação JSON em caracteres;
- relevância atual usa prioridade e recência, não semântica;
- não resume ou comprime conteúdo;
- o contexto é construído sincronicamente.

Referências: [Agent Memory](AgentMemory.md) e
[ADR-024](../adr/ADR-024-agent-memory.md).

