# Contrato Operacional dos Agentes ASEP

**Dono:** Orchestrator e responsáveis de domínio  
**Status:** ativo  
**Versão:** 0.1.0

Estas regras valem para agentes humanos ou de IA em projetos ASEP.

## Antes de agir

1. Carregue o brief, contrato, estado, fontes obrigatórias, knowledge e standards aplicáveis.
2. Confirme objetivo, escopo, autoridade, dependências, critérios de aceite e quality gates.
3. Classifique cada afirmação como fato, evidência, hipótese, decisão ou pergunta.
4. Valide entradas; interrompa quando faltar dado crítico.

## Durante o trabalho

- não invente requisitos, fatos, pesquisas, resultados, aprovações ou necessidades;
- declare hipóteses, impacto se falsas, dono e gatilho de validação;
- não invada responsabilidades de outro agente;
- registre decisões duráveis e preserve rastreabilidade;
- produza evidências para cada gate;
- revise o próprio trabalho antes do handoff;
- preserve conteúdo e dados conforme classificação;
- execute apenas mudanças autorizadas e reversíveis quando possível.

## Autoridade e limites

O contrato do agente define autoridade específica. Publicação, gasto, acesso sensível, exclusão material, mudança contratual, decisão de produto de impacto material e aceite de risco alto exigem pessoa autorizada. O Orchestrator coordena, mas não cria requisitos, decide arquitetura sozinho, implementa código, substitui especialistas nem aprova a própria entrega em conflito de interesse.

## Saída e handoff obrigatórios

Toda entrega informa: contexto; objetivo; entradas; validações; trabalho; artefatos/evidências; fatos e hipóteses; decisões; riscos; pendências; checklist; próxima ação; responsável; prazo ou gatilho. Use [core/COMMUNICATION.md](core/COMMUNICATION.md).

## Definition of Done documental

- objetivo, público, dono, versão e status claros;
- termos consistentes com o glossário;
- links internos válidos;
- checklists verificáveis;
- nenhum placeholder silencioso, segredo ou dado pessoal desnecessário;
- decisões e exceções registradas;
- localização acessível pelo README ou Registry.

## Escalonamento

Interrompa e siga [core/ESCALATION.md](core/ESCALATION.md) diante de falta de autorização, contradição crítica, risco alto, conflito de autoridade ou evidência insuficiente.
