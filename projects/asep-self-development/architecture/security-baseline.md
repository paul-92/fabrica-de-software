# Security Baseline

**ID:** ARCH-SEC-001 | **Versão:** 0.1.0 | **Status:** approved

## Modelo de confiança do MVP

Aplicação local, single-user e sem autenticação. O usuário do sistema operacional
e as permissões do filesystem formam o boundary de identidade. Aprovação registra
papel declarado para auditoria, mas não prova identidade; essa limitação é
explícita e impede uso como controle forte.

## Ativos e ameaças

| Ativo | Ameaça | Controle 0.1 |
|---|---|---|
| declarativos | adulteração/path traversal | raiz allowlist, schema, fingerprint |
| estado | corrupção/escrita parcial | lock, temp+replace, checksum/recovery |
| artefatos | sobrescrita/dado indevido | paths relativos, manifesto, classificação |
| logs/audit | segredo, truncamento | redaction, allowlist, detecção de linha parcial |
| aprovação | papel falsamente declarado | registro explícito e aviso de confiança local |
| templates | leitura fora da raiz/injeção | loader restrito, StrictUndefined, sem funções arbitrárias |

## Controles obrigatórios

`yaml.safe_load`; Pydantic com campos extras proibidos; nenhuma rede; nenhum
subprocesso no Runtime 0.1; paths normalizados; permissões herdadas com recomendação
de diretório privado; não persistir segredo; dependências fixadas e verificadas no
planejamento; mensagens sanitizadas.

## Riscos residuais

Sem autenticação, um usuário com acesso ao diretório pode editar estado e declarar
qualquer papel. Audit não é tamper-proof. Esses riscos são aceitáveis somente para
uso local/piloto e exigem nova arquitetura antes de multiusuário ou produção
regulada.

## Review futuro

Security Engineer deve validar threat model antes de `QG-SECURITY`. Nenhuma
política de IA é necessária para o fluxo sem provedor.
