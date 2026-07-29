# Fundamentos de DevOps

## Objetivo

Orientar colaboração, automação e operação para que mudanças cheguem ao usuário com segurança, feedback rápido e capacidade de recuperação.

## Conceitos principais

- **Integração e entrega contínuas:** validação frequente e preparação automatizada de mudanças.
- **Ambiente reproduzível:** configuração declarada e controlada.
- **Observabilidade:** logs, métricas e traces que permitem investigar comportamento.
- **SLI/SLO:** indicador e objetivo mensurável de confiabilidade.
- **Error budget:** margem de falha usada para equilibrar evolução e estabilidade.
- **Rollout progressivo:** exposição gradual com critérios de pausa.
- **Rollback/roll-forward:** restauração ou correção segura após falha.
- **Runbook:** instruções acionáveis para uma condição operacional.

## Boas práticas

- Automatizar build, validação, promoção e registro de versão.
- Separar ambientes e aplicar menor privilégio.
- Definir SLOs pelas jornadas críticas.
- Criar alertas acionáveis ligados a runbooks.
- Ensaiar migração, rollback, backup e restauração.
- Observar impacto e custo após cada release.

## Erros comuns

- Tratar DevOps como equipe de tickets no fim do fluxo.
- Fazer mudanças manuais sem rastreabilidade.
- Alertar sobre sintomas sem ação possível.
- Usar dashboards sem objetivos ou responsáveis.
- Fazer deploy completo quando o risco pede progressão.
- Produzir backup sem testar restauração.

## Checklist

- [ ] Artefato, configuração e versão são rastreáveis.
- [ ] Pipeline aplica gates proporcionais ao risco.
- [ ] Segredos, acessos e ambientes estão protegidos.
- [ ] SLOs, dashboards, alertas e runbooks estão conectados.
- [ ] Rollout, migração e recuperação foram ensaiados.
- [ ] Custos, capacidade e dependências são observados.

## Relação com outros departamentos

- **Architecture:** define implantação, dependências e falhas.
- **Engineering/Database:** fornecem artefatos, migrações e sinais.
- **Security:** protege cadeia de entrega, acesso e segredos.
- **Testing:** integra evidências e ambientes ao pipeline.
- **Business/Product:** definem jornadas críticas e tolerância ao impacto.

Referências internas: `../../standards/operations.md`, `../../workflows/release-operations.md` e `../../playbooks/incident-response.md`.
