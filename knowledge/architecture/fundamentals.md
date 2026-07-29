# Fundamentos de Architecture

## Objetivo

Orientar decisões estruturais que equilibrem requisitos, atributos de qualidade, risco, custo, evolução e capacidade operacional.

## Conceitos principais

- **Fronteira:** limite de responsabilidade, dados ou confiança.
- **Componente:** unidade com propósito e contrato claros.
- **Acoplamento e coesão:** dependência entre partes e foco dentro de cada parte.
- **Atributo de qualidade:** segurança, desempenho, disponibilidade, modificabilidade ou outra propriedade mensurável.
- **ADR:** contexto, opções, decisão e consequências de uma escolha relevante.
- **Trade-off:** benefício obtido ao aceitar um custo ou limitação.
- **Reversibilidade:** custo e risco para mudar uma decisão.
- **Modelo de falha:** como dependências falham e o sistema responde.

## Boas práticas

- Derivar decisões de requisitos e cenários mensuráveis.
- Definir ownership, contratos e fluxos de dados.
- Preferir simplicidade e evolução incremental.
- Comparar alternativas e registrar consequências.
- Projetar timeout, repetição segura, degradação e recuperação.
- Incluir segurança, observabilidade e custo desde o início.

## Erros comuns

- Escolher tecnologia antes de compreender o problema.
- Criar abstrações para necessidades hipotéticas.
- Desenhar apenas o caminho de sucesso.
- Centralizar dados ou responsabilidades sem ownership.
- Confundir diagrama com arquitetura suficiente.
- Ignorar migração, operação e estratégia de saída.

## Checklist

- [ ] Contexto, requisitos e restrições estão confirmados.
- [ ] Atributos de qualidade possuem cenários verificáveis.
- [ ] Fronteiras, contratos e dados estão claros.
- [ ] Falhas e recuperação foram consideradas.
- [ ] Alternativas e trade-offs estão em ADRs.
- [ ] Segurança, testes, operação e custos participaram da revisão.

## Relação com outros departamentos

- **Business/UX:** fornecem necessidades, jornadas e prioridades.
- **Backend/Frontend/Mobile/Database:** detalham e implementam decisões.
- **Security:** revisa trust boundaries e ameaças.
- **Testing:** define evidências para riscos arquiteturais.
- **DevOps:** valida implantação, observabilidade e recuperação.

Referências internas: `../../standards/architecture.md`, `../../templates/architecture-adr.md` e `../security/fundamentals.md`.
