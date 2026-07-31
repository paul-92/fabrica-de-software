# Business Engineering

## Status

- **Phase:** 10
- **Sprint:** 10.2
- **Status:** In Progress

---

# Missão

A Business Engineering é o subdomínio da ASEP responsável por transformar necessidades de negócio em um modelo estruturado, validado e independente de tecnologia.

Seu objetivo é servir como a ponte entre o problema de negócio apresentado pelo usuário e todas as demais camadas da plataforma.

Em vez de gerar código diretamente a partir de um prompt, a ASEP primeiro constrói um modelo explícito do domínio do problema.

Esse modelo torna o processo determinístico, auditável, reutilizável e compreensível tanto para humanos quanto para agentes de IA.

---

# Objetivos

A Business Engineering deve ser capaz de:

- compreender requisitos de negócio;
- identificar atores envolvidos;
- identificar casos de uso;
- organizar regras de negócio;
- representar restrições do domínio;
- estruturar entidades de negócio;
- produzir um Project Blueprint completo.

---

# Princípios

A Business Engineering segue os seguintes princípios:

1. O negócio vem antes da tecnologia.

2. Todo software representa um domínio.

3. Todo domínio deve possuir um modelo explícito.

4. O modelo de negócio deve ser independente da implementação.

5. Nenhum agente gera código sem antes existir um Project Blueprint válido.

---

# Papel dentro da ASEP

Fluxo geral:

Business Description

↓

Business Engineering

↓

Project Blueprint

↓

Planning

↓

Execution

↓

Quality Assurance

↓

Delivery

---

# Objetos de Domínio

O núcleo da Business Engineering é composto pelos seguintes objetos de domínio:

- Requirement
- Actor
- UseCase
- BusinessRule
- Entity
- Constraint
- TechnologyPreference
- ProjectBlueprint

## Aggregate Root

O Aggregate Root da Business Engineering é o **ProjectBlueprint**.

Ele representa um projeto de software em nível de negócio, independente de linguagem de programação, framework ou infraestrutura.

Todos os demais objetos pertencem ao contexto de um ProjectBlueprint.

---

# Integração com a ASEP

A Business Engineering atua como a primeira camada inteligente da plataforma.

Ela recebe uma descrição de negócio e produz um modelo estruturado que será consumido pelos demais módulos.

Fluxo previsto:

Business Description

↓

Business Engineering

↓

ProjectBlueprint

↓

Planning

↓

Execution

↓

Quality Assurance

↓

Delivery

---

# Responsabilidades

A Business Engineering é responsável por:

- estruturar requisitos;
- organizar atores;
- modelar casos de uso;
- representar regras de negócio;
- representar restrições;
- estruturar entidades do domínio;
- produzir um ProjectBlueprint consistente.

Ela **não** é responsável por:

- gerar código;
- executar agentes;
- planejar tarefas;
- executar workflows;
- realizar deploy.

Essas responsabilidades pertencem a outros módulos da ASEP.

---

# Serviços

A camada de serviços da Business Engineering é responsável por transformar informações de negócio em objetos de domínio.

## RequirementAnalyzer

O `RequirementAnalyzer` é o primeiro serviço implementado.

Sua responsabilidade é converter descrições de negócio em uma coleção estruturada de objetos `Requirement`.

Características da primeira implementação:

- determinística;
- independente de IA;
- independente de provedores externos;
- produz sempre a mesma saída para a mesma entrada;
- gera identificadores previsíveis;
- valida descrições inválidas.

Essa implementação servirá como base para futuras integrações com modelos de linguagem, mantendo a mesma interface pública.

# Roadmap

A evolução da Business Engineering seguirá as seguintes etapas:

## Sprint 10.1

- Foundation Models
- Requirement
- Actor
- UseCase
- ProjectBlueprint

_Status: Concluída_

---

## Sprint 10.2

- Arquitetura
- Documentação
- Definição do domínio

_Status: Em andamento_

---

## Sprint 10.3

- BusinessRule
- Entity
- Constraint
- TechnologyPreference

---

## Sprint 10.4

- Requirement Analyzer
- Blueprint Builder
- Business Validator

---

## Sprint 10.5

Integração com o módulo Planning.

---

## Sprint 10.6

Integração com os Agents.

---

## Sprint 10.7

Pipeline completo:

Business Description

↓

Business Engineering

↓

ProjectBlueprint

↓

Planning

↓

ExecutionPlan

↓

Agents

↓

Generation

↓

Quality Assurance

↓

Release

---

# Princípios Arquiteturais

A Business Engineering deve permanecer:

- determinística;
- independente de tecnologia;
- independente de modelos de IA;
- orientada ao domínio;
- testável;
- extensível;
- modular.

Nenhuma funcionalidade deverá comprometer esses princípios.

---

# Visão de Longo Prazo

A Business Engineering será o ponto único de entrada para qualquer descrição de negócio recebida pela ASEP.

Todo o restante da plataforma deverá trabalhar sobre um **ProjectBlueprint**, nunca diretamente sobre texto livre.

Esse princípio garante maior consistência, rastreabilidade, reprodutibilidade e capacidade de evolução da plataforma.