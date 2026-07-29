# principles

## Objetivo
Orientar decisões sobre fronteiras, coesão, acoplamento, evolução e operabilidade.

## Conceitos e limites

Este tema orienta julgamento; não substitui requisitos confirmados, decisão do
dono nem o standard aplicável. Termos e estado devem ser definidos no contexto
do projeto.

## Aplicação operacional

- Faça fronteiras refletirem responsabilidade e mudança.
- minimize acoplamento e maximize coesão.
- projete observabilidade e recuperação desde o início.

## Critérios de decisão

Compare resultado esperado, evidência, risco, restrições, custo total, capacidade,
reversibilidade e impacto operacional. Registre alternativas quando a escolha for
material.

## Erros comuns

- copiar uma solução sem verificar contexto;
- transformar hipótese em fato ou preferência em restrição;
- omitir exceções, ownership, falha ou estratégia de saída;
- produzir artefato sem ligação a requisito, decisão ou gate.

## Checklist

- [ ] Conceitos e fonte estão claros.
- [ ] As três orientações operacionais foram tratadas.
- [ ] Alternativas, exceções e riscos relevantes estão registrados.
- [ ] A decisão aponta para agente, workflow, standard e evidência.

## Relação com agentes e workflows

O especialista do domínio aplica o conteúdo; Business Analyst preserva a origem;
Architect avalia impacto sistêmico; QA transforma risco em validação. Consulte nas
fases de discovery, definição, execução e review quando aplicável.

## Referências internas

[`core/QUALITY.md`](../../core/QUALITY.md), standards e playbook do domínio,
além do contrato do agente responsável.
