# Padrão de Segurança e Privacidade

- Privilégio mínimo, deny-by-default e separação de funções.
- Autenticação e autorização validadas no servidor.
- Segredos em cofre aprovado, com rotação e sem exposição em logs.
- Criptografia em trânsito e repouso conforme classificação.
- Validação de entrada, encoding de saída e proteções contra abuso.
- Dependências, imagens e infraestrutura verificadas continuamente.
- Dados minimizados, com finalidade, base, retenção e descarte definidos.
- Logs auditáveis, protegidos e sem dados sensíveis desnecessários.
- Threat model para fluxos críticos e plano de resposta.
- Incidente ou suspeita segue `../playbooks/incident-response.md`.
