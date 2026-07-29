# Fundamentos de Mobile

## Objetivo

Orientar produtos móveis confiáveis diante de dispositivos diversos, conectividade variável, permissões e ciclos externos de distribuição.

## Conceitos principais

- **Ciclo de vida:** transições entre primeiro plano, fundo, suspensão e encerramento.
- **Offline-first:** trabalho útil e consistente mesmo sem conexão, quando requerido.
- **Sincronização:** reconciliação entre estados local e remoto.
- **Permissão:** acesso revogável a capacidade ou dado do dispositivo.
- **Deep link:** entrada que conduz a contexto interno específico.
- **Distribuição:** assinatura, revisão, rollout e atualização por lojas ou canais corporativos.
- **Compatibilidade:** conjunto explícito de sistemas e dispositivos suportados.

## Boas práticas

- Projetar para rede lenta, interrupção e retomada.
- Solicitar permissão no contexto de uso e explicar valor.
- Minimizar dados locais e protegê-los conforme classificação.
- Definir política de conflito e repetição na sincronização.
- Observar crashes, consumo, latência e adoção de versão.
- Planejar beta, rollout gradual e compatibilidade de API.

## Erros comuns

- Assumir conectividade contínua.
- Pedir todas as permissões no primeiro uso.
- Guardar segredos ou dados sensíveis sem proteção adequada.
- Ignorar versões antigas durante evolução do backend.
- Tratar aprovação da loja como etapa instantânea.
- Replicar a interface web sem considerar contexto móvel.

## Checklist

- [ ] Plataformas e versões suportadas estão definidas.
- [ ] Ciclo de vida, offline e sincronização foram avaliados.
- [ ] Permissões são mínimas, contextuais e revogáveis.
- [ ] Acessibilidade e tamanhos de tela foram validados.
- [ ] Distribuição, assinatura e rollback possuem plano.
- [ ] Telemetria cobre estabilidade sem invadir privacidade.

## Relação com outros departamentos

- **UX:** considera contexto, gestos, conteúdo e acessibilidade móvel.
- **Backend:** garante contratos compatíveis e sincronização segura.
- **Security:** revisa armazenamento, permissões e identidade.
- **Testing:** cobre dispositivos, versões, rede e ciclo de vida.
- **DevOps:** coordena assinatura, distribuição e observabilidade.

Referências internas: `../../playbooks/mobile-app.md`, `../../standards/security-privacy.md` e `../testing/fundamentals.md`.
