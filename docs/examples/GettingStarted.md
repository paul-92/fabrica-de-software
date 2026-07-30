# Getting Started — Pipeline E2E

**Público:** pessoas integrando a ASEP  
**Status:** vigente

Instale o pacote:

```bash
python -m pip install -e ".[test]"
```

Execute:

```python
import asep

result = asep.execute(
    goal="Analise este projeto e explique sua arquitetura.",
    workspace=".",
)

print(result.status)
print(result.summary)
print(result.metrics["tools"]["total"])
```

O workspace deve existir e conter `README.md` e
`docs/architecture/ArchitectureMap.md` para a composição padrão. Paths
absolutos nos payloads de Tool, `.git`, `.env` e credenciais são bloqueados.

Exemplos executáveis:

- `examples/basic_analysis.py`;
- `examples/directory_summary.py`;
- `examples/architecture_overview.py`.

O pipeline é determinístico e não usa LLM. Metadata sensível é removida antes
de persistência ou retorno.
