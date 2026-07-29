# CLI Design

**ID:** ARCH-CLI-001 | **Versão:** 0.1.0 | **Status:** approved

## Comandos MVP

```text
asep project init PATH
asep validate [PATH]
asep workflow start PROJECT --workflow ID
asep run next PROJECT
asep status PROJECT [--json]
asep approve PROJECT REQUEST_ID --as ROLE [--reason TEXT]
asep reject PROJECT REQUEST_ID --as ROLE --reason TEXT
asep resume PROJECT [--stage ID]
asep cancel PROJECT --reason TEXT
```

`--json` usa saída de máquina da biblioteca padrão; Rich é apenas apresentação
humana. Comandos mutáveis exibem resumo e pedem confirmação quando material; uma
opção explícita não interativa poderá existir apenas com contrato claro no plano.

## Códigos de saída

`0` sucesso; `2` uso/entrada; `3` validação; `4` bloqueado/aguardando aprovação;
`5` falha de execução; `6` conflito de estado; `7` cancelado. Mensagem contém
código estável, explicação segura e próxima ação.

## Segurança e usabilidade

Paths são resolvidos sob workspace/projeto; segredos não entram em flags nem
logs; rejeição exige motivo; status não altera estado. Help e erros são testados
com `CliRunner`.

## Fora do escopo

Shell interativo, TUI, autocomplete customizado, daemon, API, dashboard e Web.
