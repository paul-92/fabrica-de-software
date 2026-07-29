# Proposta de MVP — MoSCoW

**ID:** BA-MVP-001 | **Versão:** 0.1.1 | **Status:** aprovado pelo Product Owner  
**Dono:** Business Analyst | **Data:** 2026-07-28

## Princípio de recorte

O MVP candidato deve provar que o modelo ASEP controla uma execução auditável. Não
precisa executar especialistas por IA nem resolver colaboração remota.

## Must aprovados

- criar/abrir projeto e fixar `software-project`;
- carregar/validar Registry, contratos e referências;
- instanciar etapas e executar sequência;
- manter estado de projeto, etapa e tentativa;
- validar required inputs;
- registrar artefatos mínimos;
- avaliar gates e pausar para aprovação humana;
- registrar eventos e auditoria;
- falhar sem avançar, cancelar e retomar;
- operar localmente por CLI sem provedor externo de IA.

**Justificativa:** sem qualquer item acima, não se prova o lifecycle, a governança
ou a recuperação que diferenciam a ASEP de scripts/prompts isolados.

## Should

- consulta de estado sem mutação;
- mensagens de diagnóstico e próxima ação consistentes;
- validação de compatibilidade antes de iniciar a execução;
- comando de simulação/planejamento sem efeitos.

## Could

- recomendação automática de workflow sujeita a confirmação;
- exportação de relatório consolidado;
- adaptador opcional para um executor externo autorizado.

## Won't now

- paralelismo;
- GUI;
- serviço remoto/multiusuário;
- autenticação;
- banco de dados;
- dashboard;
- integração obrigatória com IA;
- execução autônoma de agentes;
- marketplace/editor visual;
- decisões de stack.

## Aprovação

Paulo Cesar aprovou este recorte para a versão 0.1 em 2026-07-28. `Should` e
`Could` não entram automaticamente no compromisso; exigem capacidade e change
control caso afetem a baseline.
