# Padrão de documentação da ASEP

**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

Documentação é parte do produto. Deve permitir operação, manutenção, auditoria
e continuidade sem depender de conversas externas.

## Princípios

- explicar primeiro em linguagem simples e depois no nível técnico necessário;
- tratar código e testes como fonte da verdade sobre comportamento;
- manter documentos vivos, datados, versionados, com dono e status;
- não documentar funções planejadas como existentes;
- reutilizar e atualizar documentos canônicos, evitando duplicação;
- registrar decisões duráveis em ADRs e evolução na história arquitetural;
- manter Glossário, mapa de arquitetura e mapa de dependências coerentes;
- relacionar requisito, implementação, teste, decisão e limitação;
- não incluir segredo, dado pessoal ou placeholder silencioso.

## Por Sprint

Quando aplicável, atualizar:

- fotografia da Sprint/Fase;
- índice e README;
- arquitetura e dependências;
- Roadmap e história;
- glossário;
- ADR apenas quando existir decisão arquitetural relevante;
- comandos, resultados de teste e limitações observadas.

## Checklist de qualidade

- [ ] objetivo, público, dono, versão e status estão claros;
- [ ] afirmações correspondem ao código ou estão marcadas como plano/hipótese;
- [ ] termos estão consistentes com o glossário;
- [ ] links relativos funcionam;
- [ ] comandos são reais e reproduzíveis;
- [ ] decisões e exceções têm rastreabilidade;
- [ ] nenhum segredo ou dado pessoal foi incluído;
- [ ] não há conteúdo duplicado ou contraditório;
- [ ] índice e pontos de entrada foram atualizados;
- [ ] `git diff --check` e validação de links foram executados.
- [ ] métricas e status de release distinguem validação local de publicação.
