# Fundamentos de Testing

## Objetivo

Orientar a produção de evidência suficiente para decidir se uma mudança atende aos requisitos com risco residual conhecido.

## Conceitos principais

- **Risco de qualidade:** chance de falha e impacto para usuário ou negócio.
- **Oráculo:** fonte usada para determinar o resultado esperado.
- **Nível de teste:** unidade, componente, integração, sistema ou jornada.
- **Teste funcional e não funcional:** comportamento e atributos de qualidade.
- **Regressão:** perda de comportamento anteriormente válido.
- **Pirâmide de testes:** distribuição que favorece feedback rápido e reserva testes amplos para riscos de integração.
- **Flaky test:** teste cujo resultado varia sem mudança relevante.
- **Evidência:** resultado observável, ambiente, dados e versão associados.

## Boas práticas

- Derivar testes de riscos, requisitos, regras e falhas históricas.
- Testar cedo no nível mais econômico capaz de detectar o problema.
- Cobrir caminhos principal, alternativo, erro e permissão.
- Manter testes determinísticos, independentes e diagnosticáveis.
- Usar dados sintéticos ou autorizados.
- Revisar risco residual antes do release.

## Erros comuns

- Usar percentual de cobertura como sinônimo de confiança.
- Automatizar cenários instáveis sem corrigir a causa.
- Concentrar validação apenas no fim.
- Testar implementação e impedir refatoração segura.
- Ignorar ambiente, dados e versão da evidência.
- Aprovar release sem validar recuperação e observabilidade.

## Checklist

- [ ] Riscos e critérios possuem testes correspondentes.
- [ ] O nível de teste é proporcional ao custo e ao risco.
- [ ] Casos negativos, limites e concorrência aplicáveis foram cobertos.
- [ ] Segurança, acessibilidade e desempenho foram avaliados.
- [ ] Evidências são reproduzíveis e ligadas à versão.
- [ ] Defeitos e risco residual possuem decisão registrada.

## Relação com outros departamentos

- **Business/Product:** fornecem regras e critérios de aceite.
- **UX:** define sucesso de jornada e acessibilidade.
- **Engineering:** torna componentes testáveis e corrige causas.
- **Security:** define cenários de ameaça e abuso.
- **DevOps:** fornece ambientes, dados, pipeline e observabilidade.

Referências internas: `../../standards/engineering-quality.md`, `../../standards/definition-of-done.md` e `../../templates/quality-release.md`.
