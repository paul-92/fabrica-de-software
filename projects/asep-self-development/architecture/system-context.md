# System Context

**ID:** ARCH-CTX-001 | **Versão:** 0.1.0 | **Status:** approved  
**Dono:** Software Architect

## Atores e sistemas

| Elemento | Papel | Troca com ASEP CLI |
|---|---|---|
| Operador local | inicia e controla execução | comandos, confirmações, estado e erros |
| Aprovador humano | decide gates materiais | decisão, autoridade, justificativa e condições |
| Mantenedor | mantém declarativos/templates | YAML/Markdown versionados |
| Filesystem local | persistência do MVP | estado, artefatos, logs e auditoria |
| Relógio/SO | timestamps e operações atômicas | UTC, lock e replace |

Não existem sistemas externos obrigatórios. Provedores de IA são fronteira futura
inativa e não participam do fluxo 0.1.

## Trust boundaries

1. entrada CLI → aplicação: todo parâmetro é não confiável;
2. YAML/Markdown → loaders: arquivos podem estar inválidos ou adulterados;
3. aplicação → filesystem: caminhos precisam permanecer no workspace/projeto;
4. humano → Approval Manager: autoridade é declarada, não autenticada no MVP;
5. templates → renderizador: variáveis devem ser allowlisted e `StrictUndefined`.

## Contexto de execução

Uma execução pertence a um projeto, fixa as versões de Registry, contratos e
workflow e usa um diretório local sob controle do operador. Não há sincronização
entre máquinas ou usuários.

## Riscos contextuais

- confiança no usuário local e na identidade declarada;
- corrupção ou edição manual concorrente;
- path traversal em referências;
- dados sensíveis em artefatos/logs;
- relógio incorreto afetar ordem aparente.

Controles e riscos residuais estão em [security-baseline.md](security-baseline.md).
