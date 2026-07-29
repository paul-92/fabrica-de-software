# Modelo de Status

**Dono:** Orchestrator | **Status:** especificação | **Versão:** 0.1.1

`planned` não satisfaz precondições; `ready` pode iniciar; `running` executa;
`awaiting_approval` espera autoridade; `blocked` espera dependência; `failed`
terminou com falha; `completed` concluiu critérios; `cancelled` foi encerrado.

Transições: `planned → ready|cancelled`; `ready → running|cancelled`;
`running → awaiting_approval|blocked|failed|completed|cancelled`;
`awaiting_approval → running|blocked|completed|cancelled`;
`blocked → ready|cancelled`; `failed → ready|cancelled` por nova tentativa.

Toda transição registra estado anterior/novo, ator, autoridade, motivo, timestamp,
trace e evidência. Estados terminais não são reabertos.
