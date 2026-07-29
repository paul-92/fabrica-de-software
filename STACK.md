# Política de Stack Tecnológica

**Dono:** Tech Lead  
**Status:** ativo  
**Versão:** 0.1.0

A ASEP não fixa stack universal. Cada projeto registra escolhas, versões, alternativas e estratégia de saída em seu documento de arquitetura e ADRs.

## Critérios de decisão, em ordem

1. requisitos funcionais e atributos de qualidade;
2. segurança, privacidade, acessibilidade e suporte;
3. capacidade da equipe e manutenção;
4. operabilidade, observabilidade e recuperação;
5. custo total, portabilidade e lock-in;
6. maturidade do ecossistema;
7. velocidade inicial.

## Guardrails

- tecnologia crítica precisa de dono, versão suportada e política de atualização;
- novidade material exige alternativas, riscos, PoC limitada quando necessário e ADR;
- dados sensíveis só usam serviços avaliados e autorizados;
- credenciais ficam em cofre aprovado;
- duplicação de ferramentas exige justificativa;
- decisão tecnológica não pode antecipar requisitos ainda não validados.

## Ciclo de vida

Componentes recebem estado `adopt`, `trial`, `assess` ou `hold`. Projetos revisam suporte, vulnerabilidades, licenças, custo e dependências abandonadas. O padrão aplicável está em [standards/versioning.md](standards/versioning.md) e [standards/architecture.md](standards/architecture.md).
