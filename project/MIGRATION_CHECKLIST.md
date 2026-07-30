# Checklist de migração da ASEP

**Dono:** Engenharia ASEP  
**Versão:** 1.0  
**Status:** vigente em 2026-07-30

Este checklist preserva código, conhecimento e estado local sem incluir
credenciais no Git.

## Antes de sair da máquina antiga

- [ ] Executar `git status --short` e revisar cada alteração.
- [ ] Confirmar o branch com `git branch --show-current`.
- [ ] Criar commits intencionais para o trabalho que deve ser preservado.
- [ ] Executar `git push` e confirmar que o remote contém todos os commits.
- [ ] Conferir branches e tags importantes com `git branch -avv` e `git tag`.
- [ ] Registrar `python --version` e `python -c "import platform; print(platform.platform())"`.
- [ ] Confirmar que `python -m pip install -e ".[test]"` reproduz o ambiente.
- [ ] Registrar somente os nomes das variáveis de ambiente necessárias.
- [ ] Parar a aplicação antes de copiar qualquer banco SQLite.
- [ ] Copiar o banco local, se existir, para mídia segura:
  `Copy-Item -LiteralPath storage/asep.db -Destination <BACKUP_SEGURO>`.
- [ ] Como alternativa, se o cliente `sqlite3` estiver instalado, executar:
  `sqlite3 storage/asep.db ".backup '<BACKUP_SEGURO>/asep.db'"`.
- [ ] Copiar, se forem necessários, os diretórios locais ignorados:
  `projects/asep-self-development/.asep`,
  `projects/asep-self-development/artifacts/runs` e
  `projects/asep-self-development/logs/runs`.
- [ ] Registrar ferramentas externas: Git, Python e, para execução real do
  provider, Codex CLI. O cliente `sqlite3` é opcional.
- [ ] Registrar extensões de IDE úteis manualmente; elas não são requisito do
  projeto.
- [ ] Revisar arquivos rastreados em busca de segredos e usar um scanner de
  histórico antes da transferência definitiva.
- [ ] Executar `python scripts/verify_environment.py`.
- [ ] Executar `python -m pytest -v`.
- [ ] Executar `python -m compileall src tests`.
- [ ] Executar `git diff --check`.

### Bloqueios concretos desta fotografia

- [ ] Publicar o commit local `863766f`, ausente no remote tracking branch.
- [ ] Revisar, versionar e publicar as mudanças locais da Fase 8.
- [ ] Não considerar o remoto como backup completo até concluir os dois itens.

## Na máquina nova

- [ ] Instalar Git.
- [ ] Instalar CPython 3.12 ou superior.
- [ ] Clonar o repositório e executar
  `git switch feature/sprint-3-core-architecture`, salvo mudança registrada em
  [PROJECT_STATE.md](PROJECT_STATE.md).
- [ ] Criar e ativar `.venv` conforme [BOOTSTRAP.md](../BOOTSTRAP.md).
- [ ] Executar `python -m pip install -e ".[test]"`.
- [ ] Copiar `.env.example` para `.env` apenas como referência e configurar as
  variáveis no shell ou IDE; a aplicação não carrega `.env` automaticamente.
- [ ] Restaurar banco e diretórios ignorados somente se o histórico local for
  necessário.
- [ ] Executar `python scripts/verify_environment.py`.
- [ ] Executar a suíte e `compileall`.
- [ ] Executar `asep --help` e um fluxo de teste apropriado.
- [ ] Validar a persistência selecionada (`memory`, `file` ou `sqlite`).
- [ ] Validar consultas de Run e Timeline.
- [ ] Validar Metrics e Dashboard API.
- [ ] Ler [PROJECT_STATE.md](PROJECT_STATE.md) e
  [NEXT_STEPS.md](NEXT_STEPS.md).

## Depois da migração

- [ ] Confirmar que testes, CLI e API funcionam.
- [ ] Conferir diferenças de paths, permissões, encoding e diretório temporário.
- [ ] Atualizar o inventário se Python, sistema ou ferramentas mudaram.
- [ ] Remover cópias temporárias inseguras após validar o backup definitivo.
- [ ] Criar commit somente para ajustes realmente necessários de compatibilidade.
- [ ] Não apagar a máquina antiga antes de comparar commits e dados restaurados.

## Classificação dos dados

| Item | Classificação | Ação |
|---|---|---|
| `storage/asep.db` | estado local gerado; ausente nesta fotografia | backup opcional, não versionar |
| `.asep/` do projeto | estado local de execução | copiar separadamente se necessário |
| `artifacts/runs/` | artefatos gerados por runs | copiar separadamente se necessário |
| `logs/runs/` | logs locais | copiar somente se necessários e autorizados |
| bancos de testes | fixtures temporárias/descartáveis | recriar pela suíte |
| código, docs, ADRs e prompts | fonte versionada | preservar por commit e push |

