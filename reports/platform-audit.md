# Auditoria da Plataforma ASEP

**Data:** 2026-07-28  
**Responsável:** Documentation Engineer, com validação estrutural automatizada  
**Status:** concluída  
**Versão auditada:** 0.1.1

## Objetivo e escopo

Revisar integralmente a fundação documental da ASEP quanto a sintaxe YAML, links,
Registry, contratos, workflows, quality gates, duplicações, contradições,
profundidade dos documentos e finalidade das pastas. A auditoria não autorizou
nem implementou código de produção.

## Estrutura auditada

Foram examinados 365 arquivos: 326 Markdown, 36 YAML e três utilitários locais de
manutenção/validação. A plataforma contém 15 agentes, 15 contratos, 16 papéis,
10 departamentos, sete workflows declarativos, 20 workflows operacionais e
13 quality gates.

## Problemas encontrados nesta revisão

1. **Duplicação superficial:** 19 standards, 27 templates e nove documentos de
   Runtime tinham corpos idênticos; vários workflows diferiam quase só pelo nome.
2. **Contratos semanticamente fracos:** `role` e `department` não usavam os IDs
   dos Registries; o Orchestrator reportava a si próprio; entradas genéricas não
   possuíam produtores canônicos verificáveis.
3. **Registry incompleto semanticamente:** a lista de agentes de cada workflow
   não refletia todos os agentes atribuídos no YAML executável.
4. **Especialização insuficiente:** agentes, papéis, departamentos e artigos de
   knowledge repetiam orientação genérica em excesso.
5. **Pastas ambíguas:** READMEs de cliente, projeto-modelo e projeto piloto não
   definiam conteúdo permitido, limites e regra de entrada.
6. **Sobreposição histórica:** templates e workflows agregados anteriores não
   indicavam claramente os documentos canônicos atuais.
7. **Corrupção de texto:** arquivos de observabilidade continham caracteres de
   controle introduzidos pela interpretação de backticks no utilitário inicial.
8. **Validação incompleta:** o validador anterior verificava existência, mas não
   IDs organizacionais, produtores de entradas, autorreferência ou paridade do
   Registry de workflows.

## Correções realizadas

- contratos normalizados para IDs reais de papéis/departamentos e `reports_to`
  coerente;
- required inputs e outputs substituídos por nomes canônicos com produtores
  conhecidos;
- Registry de workflows sincronizado com os agentes realmente atribuídos;
- standards reescritos com regra obrigatória, recomendação, opção contextual,
  exceção e evidência específicas;
- templates diferenciados pelos campos necessários a cada artefato;
- Runtime, workflows, agentes, papéis, departamentos e knowledge enriquecidos
  com procedimentos e critérios próprios de domínio;
- READMEs de pastas passaram a definir finalidade, entrada e conteúdo proibido;
- documentos agregados históricos marcados como compatibilidade, com indicação
  do canônico;
- observabilidade reescrita e limpa;
- validador ampliado com verificações semânticas e caracteres de controle.

Nenhum arquivo histórico útil foi apagado.

## Evidências de validação

| Verificação | Resultado |
|---|---|
| parsing dos 36 YAML | aprovado |
| links Markdown locais | zero quebrado |
| caminhos do Registry | todos existentes |
| agentes × contratos | 15 × 15, correspondência integral |
| roles/departments dos contratos | todos registrados |
| required inputs | todos com produtor ou entrada externa canônica |
| next agents | todos existentes; zero ciclo acidental |
| agentes dos workflows × Registry | paridade integral |
| quality gates referenciados | todos entre os 13 registrados |
| estrutura dos agentes | 27 seções em todos os 15 |
| arquivos/pastas vazios | zero |
| caracteres de controle inválidos | zero |
| conteúdo com hash duplicado | zero grupo |

Comando reproduzível: `python tools/validate-asep.py`.

## Contradições e redundâncias residuais

- documentos históricos agrupados em `agents/`, standards compostos antigos,
  prompts e playbooks por tipo de produto continuam fora do Registry. Eles foram
  preservados como referência; a política de depreciação definitiva ainda deverá
  ser aplicada durante a release 0.2;
- contratos agora têm compatibilidade nominal verificável, mas ainda não existem
  schemas formais por tipo de artefato para validar conteúdo;
- o Registry é manual e pode divergir no futuro caso o validador não seja
  executado como gate;
- métricas, tracing e auditoria são especificações, não evidência de operação real.

## Riscos e recomendações

1. Criar schemas versionados e testes positivos/negativos na release 0.2.
2. Tornar `tools/validate-asep.py` gate obrigatório de mudança documental.
3. Executar um piloto documental pequeno antes de escolher tecnologia.
4. Deprecar documentos históricos somente após verificar projetos consumidores.
5. Não declarar Runtime, Orchestrator ou observabilidade como implementados.
