# ADR-014 — Credencial inicial do bootstrap

**ID:** ADR-014 | **Versão:** 1.0.0 | **Status:** approved  
**Dono:** autoridade do projeto | **Data:** 2026-08-29  
**Escopo:** TaskFlow Sprint 2 — Banco, organizations, autenticação e usuários

## Contexto

A Fase 0 aprovou um bootstrap administrativo seguro, transacional e idempotente,
mas manteve duas alternativas para a credencial inicial: senha fornecida por
secret com troca obrigatória, ou convite/token de ativação de uso único.

## Decisão

Adotar **convite/token de ativação de uso único**. A alternativa de senha
inicial via secret com troca obrigatória não será utilizada.

O fluxo conceitual aprovado é:

```text
organização
→ usuário ADMIN
→ membership ADMIN
→ token de ativação
→ definição da senha pelo próprio usuário
→ ativação da conta
```

## Contrato obrigatório

- token criptograficamente seguro;
- somente o hash do token é persistido;
- token de uso único e com expiração obrigatória;
- token invalidado após a ativação;
- token expirado ou reutilizado deve falhar;
- token, hash, senha ou outro secret não pode aparecer em logs;
- nenhuma senha é gerada automaticamente para o usuário;
- o usuário define a própria senha;
- bootstrap permanece idempotente;
- isolamento por `organizationId` é preservado;
- desenvolvimento e testes usam a abstração/interface de e-mail e fake já
  prevista pela arquitetura;
- serviço externo real de e-mail fica fora da Sprint 2 sem nova decisão.

## Consequências

- o bootstrap cria a identidade e membership administrativa sem estabelecer
  senha em nome do usuário;
- consumo e invalidação do token devem ser atômicos;
- testes devem cobrir expiração, reutilização, idempotência, isolamento e
  ausência de secrets em logs;
- qualquer dependência externa necessária continua sujeita ao dependency
  planning e à aprovação humana de versão exata.

## Evidência de aprovação

Decisão humana explícita recebida em 2026-08-29. Esta decisão resolve somente a
alternativa arquitetural do bootstrap e não autoriza execution da Sprint 2.
