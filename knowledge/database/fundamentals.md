# Fundamentos de Database

## Objetivo

Orientar decisões de dados que preservem significado, integridade, privacidade, desempenho e recuperação.

## Conceitos principais

- **Modelo conceitual, lógico e físico:** níveis distintos entre significado, estrutura e implementação.
- **Integridade:** validade e coerência dos dados.
- **Consistência:** garantias observáveis durante mudanças concorrentes.
- **Índice:** estrutura que troca custo de escrita e espaço por acesso eficiente.
- **Migração:** mudança controlada de estrutura ou conteúdo.
- **Retenção:** período e condição de manutenção dos dados.
- **Backup e restauração:** cópia recuperável e processo verificado de retorno.
- **Ownership:** responsabilidade pela definição e qualidade de um domínio de dados.

## Boas práticas

- Modelar pelo domínio e pelos padrões de acesso confirmados.
- Aplicar restrições de integridade próximas aos dados.
- Planejar migrações graduais, compatíveis e observáveis.
- Tratar dados pessoais por finalidade e minimização.
- Medir consultas e capacidade antes de otimizar.
- Testar restauração, não apenas geração de backup.

## Erros comuns

- Escolher banco antes de conhecer modelo e acesso.
- Usar texto livre para conceitos com regras claras.
- Remover ou renomear estruturas sem transição.
- Criar índice sem observar impacto em escrita.
- Replicar dados sem definir fonte de verdade.
- Confundir backup existente com recuperação comprovada.

## Checklist

- [ ] Ownership e fonte de verdade estão definidos.
- [ ] Invariantes e relações possuem proteção.
- [ ] Acesso, volume e crescimento são conhecidos ou marcados como lacuna.
- [ ] Migração, compatibilidade e rollback foram avaliados.
- [ ] Classificação, retenção e descarte estão documentados.
- [ ] Backup e restauração possuem evidência periódica.

## Relação com outros departamentos

- **Business:** define significado, regras e obrigações de retenção.
- **Architecture/Backend:** alinham ownership, consistência e padrões de acesso.
- **Security:** define acesso, criptografia, auditoria e minimização.
- **Testing:** valida migrações, integridade e recuperação.
- **DevOps:** automatiza operação, monitoramento e restauração.

Referências internas: `../../standards/api-data-saas.md`, `../../standards/security-privacy.md` e `../backend/fundamentals.md`.
