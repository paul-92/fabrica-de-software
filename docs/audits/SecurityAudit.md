# Auditoria de segurança — RC1

**Dono:** Segurança/Engenharia ASEP | **Versão:** 1.0 | **Status:** concluída em 2026-07-30

## Escopo

`.gitignore`, `.env.example`, padrões de credenciais em arquivos rastreados,
SQLite, logs, subprocess, serialização, metadados e dados ignorados.

## Resultado

Nenhum sinal de segredo foi encontrado pelo scan de padrões em código e
configuração rastreados. Isso não substitui scanner de todo o histórico Git.

Controles confirmados:

- `.env` é ignorado e `.env.example` contém apenas defaults seguros;
- bancos `*.db`, SQLite e `storage/` são ignorados;
- logs/runs/artefatos locais são ignorados;
- paths de artefatos e arquivos produzidos rejeitam traversal;
- serializers rejeitam objetos não JSON;
- escrita file usa temporário no mesmo filesystem;
- SQLite usa parâmetros, não concatenação de dados em SQL;
- não há import dinâmico ou execução de agente por nome não confiável.

## Riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| metadata pode receber conteúdo sensível válido em JSON | média | classificação e revisão no produtor |
| `CodexProviderConfig.environment` é serializável/repr padrão | média | não registrar config; futura marcação de campos secretos se necessário |
| logs e artefatos locais podem conter dados do projeto | média | backup/autorização e retenção |
| histórico Git não foi varrido por scanner dedicado | média | executar scanner antes do release |
| SQLite não possui criptografia | baixa/média conforme dados | proteger filesystem e não armazenar segredo |

## Pendências

Rotação/remoção de segredo deve ocorrer fora desta Sprint caso scanner histórico
encontre evidência. Nenhuma credencial foi copiada para os relatórios.

