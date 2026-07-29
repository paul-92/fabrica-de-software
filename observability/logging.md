# Logging

**Dono:** Operations | **Status:** especificação | **Versão:** 0.1.1

## Estrutura obrigatória

Registros usam timestamp UTC, nível, componente, `event_type`, `trace_id`,
`correlation_id`, IDs de execução, ator não sensível, resultado, código de erro,
`schema_version` e classificação.

## Proteção

- mensagens descrevem evento e ação, não prompts integrais;
- segredos, tokens e payloads pessoais são removidos na origem;
- campos livres são limitados e normalizados;
- acesso, retenção, integridade e descarte seguem classificação;
- falha de redaction é incidente de segurança.

## Evidência

Schema validado, amostra sanitizada, teste de correlação, política de retenção e
consulta que reconstrói uma execução sem conteúdo confidencial.
