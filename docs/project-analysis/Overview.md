# Project Analysis — visão geral

**Público:** engenharia e consumidores da API Python  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

O pacote `asep.project_analysis` transforma uma árvore local em um
`ProjectAnalysis` imutável. A análise é determinística: não usa LLM, rede,
Agent Runtime ou provider.

```text
Path -> Scanner -> Detectores -> Statistics -> ReportBuilder
                                             -> ProjectAnalysis
```

O resultado reúne linguagens, frameworks, gerenciadores, módulos, entrypoints,
arquiteturas, dependências, estatísticas, metadata e horário da análise.

```python
from pathlib import Path
from asep.project_analysis import ProjectAnalyzer

analysis = ProjectAnalyzer().analyze(Path("my_project"))
print(analysis.statistics.lines_of_code)
```

Limites: heurísticas podem produzir falsos negativos; dependências transitivas
não são resolvidas; arquivos ilegíveis são ignorados; nenhuma inferência por IA
é realizada.

Veja [ProjectAnalyzer](ProjectAnalyzer.md), [Heuristics](Heuristics.md) e
[ADR-029](../adr/ADR-029-project-analyzer.md).
