# Component Model

**ID:** ARCH-CMP-001 | **Versão:** 0.1.0 | **Status:** approved  
**Dono:** Software Architect

## Componentes e dependências

```text
CLI
 └─ Command Service
    ├─ Project Loader
    ├─ Orchestrator
    │  ├─ Registry / Contract / Workflow Loaders
    │  ├─ Workflow Engine
    │  ├─ Agent Runtime → Business Analyst Adapter
    │  ├─ Input Validator
    │  ├─ Quality Gate Evaluator
    │  ├─ Human Approval Manager
    │  └─ Error Handler
    ├─ State Manager
    ├─ Artifact Manager
    └─ Event Logger → Audit Trail
```

## Regras de acoplamento

- CLI depende de casos de uso, nunca de loaders concretos;
- Workflow Engine conhece modelos de domínio, não YAML;
- Orchestrator coordena, mas delega transição ao State Manager e validação aos
  componentes especializados;
- Runtime executa `AgentPort`; Business Analyst é um adaptador;
- Logging observa eventos; não decide estado;
- Audit Trail recebe eventos imutáveis após a transação de estado;
- Artifact Manager não avalia gate; apenas registra evidência referenciável.

## Interfaces principais

`ProjectRepository`, `RegistryRepository`, `WorkflowRepository`,
`ContractRepository`, `StateRepository`, `ArtifactRepository`, `AuditSink`,
`AgentPort`, `Clock` e `IdGenerator`.

## Falha isolada

Cada porta retorna resultado tipado ou erro de domínio. Nenhum componente grava
estado diretamente fora do State Repository. Isso permite testes em memória sem
introduzir um banco no produto.
