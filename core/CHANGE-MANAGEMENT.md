# Gestão de Mudanças

**Dono:** Delivery Lead | **Status:** ativo | **Versão:** 0.1.1

## Classificação

Mudança editorial não altera semântica; compatível adiciona capacidade sem quebrar
consumidores; material altera escopo, prazo, custo, risco ou comportamento;
breaking change quebra contrato, workflow, schema ou interpretação existente.

## Processo

1. Registrar origem, motivo, solicitante e baseline afetada.
2. Mapear artefatos, projetos e consumidores impactados.
3. Avaliar valor, prazo, custo, arquitetura, dados, segurança e operação.
4. Comparar trocar escopo, mover prazo, adicionar capacidade, migrar ou rejeitar.
5. Definir compatibilidade, versão, migração, rollback e comunicação.
6. Obter aprovação do dono e autoridades materiais.
7. Atualizar artefatos canônicos, Registry e evidência de validação.

## Adoção e emergência

Projetos ativos adotam explicitamente a nova versão ou permanecem na versão
fixada durante a janela suportada. Emergência pode usar rito acelerado somente
para conter impacto, com registro contemporâneo quando possível, regularização,
revisão e retrospectiva obrigatórias.

## Critério de conclusão

Mudança está concluída quando consumidores foram identificados, validações passaram,
aprovações e comunicação estão registradas e rollback/migração têm responsável.
