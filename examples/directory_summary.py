"""Resume a estrutura do diretório usando o pipeline oficial."""

import asep


result = asep.execute(
    goal="Liste e resuma a estrutura deste diretório.",
    workspace=".",
)
print(result.summary)
print(f"Tools executadas: {result.metrics['tools']['total']}")
