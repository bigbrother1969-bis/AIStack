---
artifact:
  id: FDN-0002
  title: Glossary
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 1.1
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-21

relations:
  references:
    - FDN-0003
    - FDN-0004
    - FDN-0005
---

# AIStack Foundation Glossary

## Purpose

The AIStack Glossary is the official semantic reference of the project.

Every fundamental concept used by AIStack is defined exactly once.

The Glossary is the Single Point of Truth (SPOT) for terminology.

All other Knowledge Artifacts must reference these definitions rather than redefining them.

---

# Core Concepts

## AIStack

A semantic system for building, governing and exploiting the Governed Heritage of Digital Ecosystems.

---

## Governed Heritage

The governed and continuously evolving heritage describing a Digital Ecosystem.

The Governed Heritage contains every governed Knowledge Artifact required to understand, explain, maintain and evolve the Digital Ecosystem.

---

## Digital Ecosystem

A coherent set of technical, organizational and human components interacting to deliver one or more services.

A Digital Ecosystem may include infrastructure, applications, data, documentation, people, processes and governance.

---

## Knowledge

Structured information that has acquired meaning through qualification, governance and context.

Knowledge is an attribute of the Governed Heritage.

---

## Knowledge Artifact

A governed representation of knowledge.

Examples include:

- documentation
- source code
- configuration
- policies
- reports
- architecture diagrams
- ADRs
- inventories
- generated documentation

Every Knowledge Artifact belongs to the Governed Heritage.

---

## Item

The fundamental semantic object of AIStack.

An Item represents any identifiable element belonging to a Digital Ecosystem.

Items may represent technical, organizational, documentary or conceptual objects.

Item is intentionally generic and technology-independent.

---

## Qualification

The human process of assigning meaning, confidence, ownership, governance and business value to observations.

Qualification transforms observations into governed knowledge.

It represents the primary value added by human expertise within AIStack.

---

## Observation

A raw fact collected from the Digital Ecosystem.

Observations do not carry meaning by themselves.

They become knowledge only after qualification.

---

## Knowledge Provider

A component responsible for discovering observations from a Digital Ecosystem.

Knowledge Providers never interpret observations.

They only collect evidence.

---

## Location

An abstraction of where a Knowledge Artifact physically resides.

A Location hides the storage mechanism — a filesystem, a repository, a
remote host — so that the rest of AIStack reasons about artifacts
without reasoning about storage (ARC-P-014).

---

## Transport

The movement of a Knowledge Artifact from one Location to another.

Transport carries artifacts. It does not qualify them, alter them or
decide what travels: eligibility is a separate governed decision.

---

## Context Engine

The component responsible for assembling the relevant context required for reasoning.

---

## Rule Engine

The component responsible for applying explicit and governed rules.

Rules must always be explainable.

---

## AI Engine

A reasoning component operating on governed knowledge.

The AI Engine never replaces governance.

It assists reasoning and explanation.

---

## SPOT (Single Point of Truth)

The unique authoritative location where a governed knowledge element is defined.

Every governed concept has exactly one SPOT.

---

## Technical Debt

Governed knowledge describing the gap between the current state and the desired state of a Digital Ecosystem.

Technical Debt is derived knowledge.

It is produced from observations, explicit rules, evidence and documented policies.

---

## Knowledge Policy

A governed rule defining how knowledge is evaluated, qualified or interpreted.

Knowledge Policies are explicit and versioned.

---

## Engineering Method

The governed methodology used to evolve AIStack while preserving the integrity of the Governed Heritage.

---

# Request

A Request is an expression of an intended operation or objective
submitted to AIStack.

A Request does not directly execute technical operations.

A Request is transformed into an executable context through Task
resolution.

------------------------------------------------------------------------

# Task

A Task is an executable context derived from a Request.

A Task defines the context in which capabilities are resolved and
executed.

A Task does not define implementation details.

------------------------------------------------------------------------

# Capability

A Capability is a governed ability of AIStack.

It defines what AIStack can do independently from implementation
technology.

A Capability is implemented by one or more Services or Providers and
exposes executable Actions.

------------------------------------------------------------------------

# Action

An Action is the smallest executable unit of a Capability.

Actions represent concrete operations performed by AIStack capabilities.

------------------------------------------------------------------------

# KnowledgePackage

A KnowledgePackage is a transport container used to move Knowledge
Artifacts between environments.

A KnowledgePackage is not a Single Point Of Truth.

The repository remains the authoritative source of governed knowledge.

------------------------------------------------------------------------

# Package Manifest

A Package Manifest is the descriptive metadata associated with a
KnowledgePackage.

It identifies package content, origin, version and governance
information.

------------------------------------------------------------------------

# PackagingPolicy

A PackagingPolicy is a governed rule defining how KnowledgePackages are
created, validated and transported.

------------------------------------------------------------------------

# ValidationEngine

A ValidationEngine is a governance component responsible for evaluating
whether a proposed knowledge integration satisfies defined policies and
constraints.

A ValidationEngine does not perform integration.

------------------------------------------------------------------------

# IntegrationEngine

An IntegrationEngine is a governance component responsible for applying
validated knowledge changes.

Validation and integration remain separate responsibilities.

------------------------------------------------------------------------

# Knowledge State

A Knowledge State represents the governance status of a knowledge
element.

Examples:

-   validated knowledge;
-   proposed knowledge;
-   unknown knowledge;
-   conflicting knowledge;
-   rejected knowledge.

------------------------------------------------------------------------

# Governance Proposal

A Governance Proposal is a proposed change generated from analysis or
validation workflows.

A Governance Proposal requires appropriate validation before becoming
governed knowledge.

---

## Foundation

The highest governance layer of AIStack.

Foundation defines the long-term principles, concepts and philosophy of the project.
