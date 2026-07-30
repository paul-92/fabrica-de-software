# ProjectAnalyzer

**Público:** desenvolvedores Python  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

`ProjectAnalyzer` é a fachada pública. `analyze(project_path, metadata=None)`
resolve o caminho, coordena componentes injetáveis e retorna
`ProjectAnalysis`.

Modelos públicos:

- `ProjectAnalysis`;
- `LanguageStatistics`, `FrameworkDetection` e `PackageManagerDetection`;
- `ProjectModule`, `Entrypoint`, `Dependency`;
- `ArchitectureDetection` e `ProjectStatistics`.

Todos usam Pydantic com `extra="forbid"` e `frozen=True`. `generated_at` exige
timezone. Caminho inexistente gera `ValueError` explícito.

O Analyzer não lê Registry, não inicia agente, não persiste resultado e não
conhece Workflow ou Pipeline.
