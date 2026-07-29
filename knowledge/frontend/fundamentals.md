# Fundamentos de Frontend

## Objetivo

Orientar experiências web acessíveis, responsivas, previsíveis e eficientes, preservando contratos e segurança.

## Conceitos principais

- **Semântica:** significado estrutural interpretável por navegador e tecnologias assistivas.
- **Estado de interface:** representação de carregamento, sucesso, vazio, erro e permissão.
- **Renderização:** momento e local em que conteúdo se torna utilizável.
- **Design responsivo:** adaptação ao espaço, conteúdo e modo de interação.
- **Progressive enhancement:** experiência básica funcional enriquecida conforme capacidade.
- **Orçamento de desempenho:** limite mensurável de custo para uma jornada.
- **Contrato de componente:** propriedades, estados, eventos e garantias.

## Boas práticas

- Começar por HTML semântico, teclado e foco.
- Modelar todos os estados e caminhos de recuperação.
- Manter estado no menor escopo necessário.
- Validar dados por experiência, sem substituir validação do servidor.
- Reutilizar componentes por comportamento comprovadamente comum.
- Medir desempenho em dispositivos e redes representativos.

## Erros comuns

- Usar elementos visuais sem semântica ou teclado.
- Exibir erro sem explicar recuperação.
- Duplicar estado derivável ou criar estado global por conveniência.
- Carregar recursos antes de serem necessários.
- Acoplar interface ao formato interno do backend.
- Considerar uma captura de tela como especificação completa.

## Checklist

- [ ] Jornada funciona por teclado e com foco visível.
- [ ] Estados vazio, carregamento, erro e permissão existem.
- [ ] Layout suporta conteúdo e tamanhos relevantes.
- [ ] Contratos e falhas do backend são tratados.
- [ ] Desempenho atende ao orçamento acordado.
- [ ] Telemetria respeita consentimento e privacidade.

## Relação com outros departamentos

- **UX:** define intenção, fluxo, conteúdo e acessibilidade.
- **Backend:** mantém contratos e tratamento consistente de erros.
- **Security:** cobre XSS, sessão, exposição de dados e dependências.
- **Testing:** combina testes de componente, integração, jornada e acessibilidade.
- **DevOps:** cuida de build, entrega, cache e observabilidade.

Referências internas: `../../standards/accessibility-performance-seo.md`, `../ux/fundamentals.md` e `../testing/fundamentals.md`.
