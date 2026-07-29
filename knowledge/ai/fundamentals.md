# Fundamentos de AI

## Objetivo

Orientar o uso responsável de inteligência artificial em produtos e no trabalho dos agentes, com valor mensurável, supervisão e controle de risco.

## Conceitos principais

- **Caso de uso:** tarefa e resultado para os quais IA pode contribuir.
- **Modelo:** sistema probabilístico com capacidades e limites específicos.
- **Prompt/contexto:** instruções e informações fornecidas para uma execução.
- **Grounding:** apoio da resposta em fontes autorizadas.
- **Avaliação:** conjunto repetível de casos, métricas e revisão.
- **Alucinação:** conteúdo plausível sem sustentação nas fontes.
- **Human-in-the-loop:** intervenção humana em decisão, revisão ou exceção.
- **Guardrail:** controle preventivo, detectivo ou limitador.
- **Drift:** mudança em dados, uso ou comportamento ao longo do tempo.

## Boas práticas

- Começar por um problema mensurável, não pela tecnologia.
- Definir quando a IA pode sugerir, agir ou deve escalar.
- Minimizar dados enviados e controlar finalidade, retenção e fornecedor.
- Fundamentar respostas em fontes autorizadas quando precisão importa.
- Avaliar qualidade, segurança, viés, custo e latência com casos representativos.
- Monitorar falhas e oferecer correção, fallback e contestação.

## Erros comuns

- Prometer determinismo para saída probabilística.
- Usar demonstração como evidência de produção.
- Enviar dados sensíveis sem autorização e controles.
- Permitir ações de impacto sem confirmação ou limite.
- Avaliar apenas respostas favoráveis.
- Ocultar do usuário limitações relevantes ou uso de IA.

## Checklist

- [ ] Caso de uso, usuário e resultado mensurável estão definidos.
- [ ] Dados, finalidade, retenção e acesso foram aprovados.
- [ ] Avaliação cobre casos normais, limites, abuso e grupos relevantes.
- [ ] Ações possuem autorização, limites e supervisão proporcionais.
- [ ] Fontes, incerteza, fallback e contestação estão previstos.
- [ ] Qualidade, custo, latência e drift são monitorados.

## Relação com outros departamentos

- **Business/Product:** definem valor, risco e decisão que pode ser automatizada.
- **UX:** comunica incerteza, controle, consentimento e recuperação.
- **Architecture/Backend:** isolam modelos, ferramentas, dados e falhas.
- **Security/Privacy:** avaliam exposição, prompt injection, abuso e terceiros.
- **Testing:** mantém avaliações reproduzíveis e critérios de regressão.
- **DevOps:** versiona prompts/modelos, observa custo e habilita rollback.

Referências internas: `../../AGENTS.md`, `../../prompts/README.md`, `../security/fundamentals.md` e `../testing/fundamentals.md`.
