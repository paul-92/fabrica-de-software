# Fundamentos de Backend

## Objetivo

Orientar serviços de servidor corretos, seguros, observáveis e fáceis de evoluir.

## Conceitos principais

- **Contrato:** comportamento público de uma API, evento ou integração.
- **Invariante:** condição que deve permanecer verdadeira.
- **Idempotência:** repetição de uma operação sem efeito adicional indevido.
- **Transação:** conjunto de mudanças que preserva consistência.
- **Concorrência:** operações simultâneas sobre recursos compartilhados.
- **Resiliência:** capacidade de limitar e recuperar falhas.
- **Autorização:** decisão sobre o que uma identidade pode fazer.
- **Observabilidade:** evidência para compreender estado e comportamento.

## Boas práticas

- Manter regras de domínio separadas de transporte e infraestrutura.
- Validar entrada e autorização no servidor.
- Definir erros, paginação, limites e compatibilidade no contrato.
- Usar timeouts, retries limitados e idempotência conscientemente.
- Propagar correlation IDs e métricas úteis.
- Planejar mudanças de dados compatíveis e reversíveis.

## Erros comuns

- Confiar em validações feitas apenas pelo cliente.
- Repetir sem limite operações não idempotentes.
- Expor detalhes internos em erros ou logs.
- Ocultar dependências e efeitos colaterais.
- Misturar regra de negócio com detalhes do framework.
- Tratar testes unitários como prova de integração.

## Checklist

- [ ] Contratos e ownership estão claros.
- [ ] Autenticação e autorização cobrem casos negativos.
- [ ] Invariantes e transações estão definidos.
- [ ] Timeout, repetição e concorrência foram avaliados.
- [ ] Logs, métricas e traces apoiam diagnóstico.
- [ ] Compatibilidade, migração e rollback foram planejados.

## Relação com outros departamentos

- **Architecture:** define fronteiras e atributos de qualidade.
- **Database:** alinha integridade, acesso, migração e retenção.
- **Frontend/Mobile:** acordam contratos e comportamento de erro.
- **Security:** revisa acesso, entrada, abuso e segredos.
- **Testing/DevOps:** validam contratos, carga, implantação e operação.

Referências internas: `../../standards/api-data-saas.md`, `../../playbooks/api.md` e `../database/fundamentals.md`.
