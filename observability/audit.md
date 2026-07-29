# Auditoria

**Dono:** Governance + Security | **Status:** especificação | **Versão:** 0.1.1

Registrar quem solicitou, executou, revisou, aprovou, cancelou e alterou; versões
de contratos/workflows; transições; evidências; exceções; acessos e exportações.

- histórico append-only no Runtime futuro;
- timestamps confiáveis e IDs estáveis;
- integridade verificável e menor privilégio;
- segregação entre autor, revisor e aprovador;
- retenção e descarte por classificação;
- correção por evento compensatório, nunca alteração silenciosa.

Revisões procuram decisão sem autoridade, autoaprovação, versão deprecada, gate
sem evidência, acesso fora do escopo e quebra de sequência.
