# Prompt reutilizável de documentação

Analise antes de editar:

1. implementação e contratos;
2. testes e resultados reproduzíveis;
3. documentação existente e seus pontos canônicos;
4. ADRs, Roadmap, história, glossários e regras em `AGENTS.md`.

Documente somente capacidades comprovadas. Diferencie fato, evidência,
hipótese, decisão, pendência e plano. Reutilize documentos existentes e evite
reescritas amplas quando uma atualização localizada for suficiente.

Conforme o impacto, atualize índice, arquitetura, dependências, história,
fotografia da Fase/Sprint, glossário e Roadmap. Crie ADR apenas quando a mudança
introduzir uma decisão arquitetural durável. Preserve links, idioma, estilo,
versionamento e rastreabilidade.

Não altere regras de negócio, não invente resultados e não exponha segredos.
Em auditorias, registre método, evidência, severidade, ação e pendência; não
declare release publicado apenas porque os testes locais passaram.
Valide links, execute os testes relevantes, `compileall` e
`git diff --check`. No relatório final informe contexto, entradas, trabalho,
evidências, decisões, riscos, pendências e próxima ação. Não faça commit ou push
sem autorização explícita.
