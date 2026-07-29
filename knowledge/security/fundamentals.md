# Fundamentos de Security

## Objetivo

Orientar a proteção proporcional de pessoas, dados, operações e sistemas durante todo o ciclo de vida do produto.

## Conceitos principais

- **Ativo:** algo de valor que precisa de proteção.
- **Ameaça, vulnerabilidade e risco:** possível causa, fraqueza explorável e combinação de probabilidade com impacto.
- **Trust boundary:** ponto em que muda o nível de confiança.
- **Privilégio mínimo:** acesso estritamente necessário por tempo adequado.
- **Defense in depth:** controles independentes em camadas.
- **Threat model:** análise de ativos, fluxos, ameaças e controles.
- **Risco residual:** risco restante após mitigação, aceito por autoridade.
- **Privacidade desde a concepção:** finalidade, minimização e proteção incorporadas ao produto.

## Boas práticas

- Modelar ameaças cedo e revisar quando fluxos mudarem.
- Autenticar identidades e autorizar cada ação sensível.
- Negar por padrão e separar funções privilegiadas.
- Gerenciar segredos fora de código, documentação e logs.
- Minimizar, classificar, reter e descartar dados conscientemente.
- Preparar detecção, contenção, recuperação e comunicação.

## Erros comuns

- Tratar ambiente interno como confiável por definição.
- Confiar em ocultação ou controles apenas no cliente.
- Coletar dados “para uso futuro” sem finalidade.
- Registrar tokens ou conteúdo sensível.
- Aplicar correções sem avaliar causa e variantes.
- Aceitar risco implicitamente por pressão de prazo.

## Checklist

- [ ] Ativos, atores, fluxos e trust boundaries estão conhecidos.
- [ ] Acesso segue privilégio mínimo e casos negativos foram considerados.
- [ ] Dados possuem finalidade, classificação, retenção e descarte.
- [ ] Segredos e dependências possuem gestão contínua.
- [ ] Controles têm evidência e risco residual tem dono.
- [ ] Incidentes possuem caminho de resposta e escalonamento.

## Relação com outros departamentos

- **Business/Legal:** esclarecem finalidade, obrigação e impacto; legal decide interpretação.
- **Architecture:** incorpora limites de confiança e controles.
- **Engineering/Database/Mobile:** implementam controles no contexto.
- **Testing:** valida abuso, autorização e resistência.
- **DevOps:** protege entrega, ambientes, segredos e resposta.
- **AI:** avalia exposição de dados, abuso e comportamento do modelo.

Referências internas: `../../standards/security-privacy.md` e `../../playbooks/incident-response.md`.
