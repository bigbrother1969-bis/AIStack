---
artifact:
  id: FDN-0004
  title: Governed Heritage
  type: Foundation Document
  version: 1.0
  status: Published
  owner: Foundation

lifecycle:
  created: 2026-07-06
  updated: 2026-07-06

relations:
  references:
    - FDN-0002
    - FDN-0003
---

# Governed Heritage

## Purpose

This document defines the central concept managed by AIStack.

The Governed Heritage is the primary asset of AIStack.

Every architectural decision, every software component and every engineering activity ultimately exists to build, govern, preserve or exploit this heritage.

See also:

- Constitution
- Foundation Glossary

---

# What is a Governed Heritage?

A Governed Heritage is the governed, qualified and continuously evolving representation of a Digital Ecosystem.

It contains every governed Knowledge Artifact required to understand, explain, maintain and evolve that ecosystem.

Unlike a software inventory or a CMDB, a Governed Heritage is not limited to describing technical assets.

It also captures the meaning, governance and relationships that transform isolated information into usable knowledge.

---

# Purpose

The purpose of the Governed Heritage is to continuously improve the understanding and evolution of a Digital Ecosystem through its Heritage.

Understanding always precedes action.

AIStack therefore seeks first to improve understanding before proposing automation.

---

# Composition

A Governed Heritage may contain, among others:

- Knowledge Artifacts
- Items
- Observations
- Qualifications
- Knowledge Policies
- Architecture descriptions
- Documentation
- Source code
- Configuration
- Infrastructure inventories
- Reports
- Evidence
- ADRs
- Rules
- Relationships
- Historical knowledge

The exact implementation is independent from this definition.

---

# Characteristics

A Governed Heritage is:

- governed
- explainable
- traceable
- portable
- transferable
- continuously evolving
- technology-independent

These characteristics remain true regardless of implementation choices.

---

# Relationship with Knowledge

Knowledge is not the Governed Heritage itself.

Knowledge is one of its attributes.

The Governed Heritage provides the structure that allows knowledge to be governed, preserved and exploited consistently.

---

# Relationship with Digital Ecosystems

Every Governed Heritage describes exactly one Digital Ecosystem.

A Digital Ecosystem may evolve.

Its Governed Heritage evolves with it.

The objective is not to preserve the ecosystem itself.

The objective is to preserve its understanding.

---

# Relationship with AI

Artificial Intelligence is not the owner of the Governed Heritage.

AI assists its exploitation.

The Governed Heritage remains governed independently of any AI model or technology.

AI engines are replaceable.

The Governed Heritage is not.

---

# Lifecycle

The Governed Heritage is continuously enriched through an explicit lifecycle:

Observation

↓

Qualification

↓

Governance

↓

Knowledge

↓

Governed Heritage

↓

Understanding

↓

Decision Support

↓

Evolution

↓

New Observations

This lifecycle is iterative.

Each evolution of the Digital Ecosystem enriches the Governed Heritage.

---

# Engineering Consequences

Every significant engineering decision should answer one question:

"How does this improve the Governed Heritage?"

If no positive impact can be identified, the long-term value of the decision should be reconsidered.

---

# Closing Statement

The Governed Heritage is the permanent memory of a Digital Ecosystem.

AIStack exists to build, govern and exploit this memory in order to continuously improve understanding, maintenance and evolution.

---

# AIStack as the First Governed Heritage

AIStack applies Governed Heritage Engineering to itself before applying it to information systems.

The project deliberately uses itself as its first case study.

Every principle, policy, engineering cycle, Knowledge Artifact and governance mechanism is first validated on AIStack itself before being generalized to external information systems.

This approach provides continuous validation of the methodology while producing a governed engineering heritage.

---

# Foundational Principle

A Governed Heritage Engineering system must first govern its own heritage before governing anyone else's.

Credibility comes from demonstration rather than assertion.

AIStack therefore considers its own repository, documentation, architecture and engineering decisions as its first governed heritage.

---

# Communication Principle

AIStack is not only built using Governed Heritage Engineering.

AIStack is the first living demonstration of Governed Heritage Engineering.

---

# Codicil

Because AIStack is its own first governed heritage.

Every architectural decision, Knowledge Artifact, migration, Context Bundle and Repository Audit contributes simultaneously to:

- improving AIStack;
- validating Governed Heritage Engineering;
- producing reusable engineering knowledge.

The project therefore continuously demonstrates the methodology while it evolves.

---

# Knowledge Transmission Principle

The Single Point Of Truth must remain unique.

However, the governed heritage must be multiply transmissible.

AIStack therefore distinguishes:

- the SPOT, where knowledge is governed;
- publication mirrors, where knowledge is distributed;
- context bundles, where knowledge is transported;
- consumers, where knowledge is used.

A mirror is not a SPOT.

A context bundle is not a SPOT.

They are governed projections of the SPOT.

---

# Deterministic Generation Principle

## Principle

Knowledge is the primary engineering asset.

Source code, documentation, tests, Docker artifacts and other implementation artifacts are derived products.

AIStack shall generate implementation from governed knowledge whenever deterministic generation is possible.

The objective is not to generate code with AI.

The objective is to generate code from governed knowledge.

## Rationale

Generated artifacts are disposable.

Improving a generator improves every artifact produced from the same governed knowledge.

Artificial Intelligence assists the creation and evolution of governed knowledge.

Deterministic generators transform that knowledge into executable artifacts.

## Consequences

AIStack progressively evolves towards a generator-based architecture.

The long-term objective is a Meta Generator capable of orchestrating specialized deterministic generators from a common governed knowledge model.

---

# Generic Kernel Principle

## Principle

The portability of AIStack is directly proportional to the amount of generic concepts implemented in the Kernel.

Technology-specific concepts shall remain outside the Kernel as replaceable implementations connected through governed contracts.

The Kernel shall depend only on stable domain concepts such as Contracts, Registries, Catalogs, Catalog Views, Selection Engines, Policies, Renderers and Generators.

Docker, Kubernetes, Nextcloud, Syncthing, Linux, Git, Proxmox and similar technologies are Knowledge Providers or specialized implementations, never Kernel concepts.

## Rationale

Every time a technology-specific concept is replaced by a generic governed concept, AIStack becomes more portable, more reusable, more maintainable and easier to extend.

The Kernel shall remain independent from technologies while technologies remain replaceable plugins around it.

The engineering objective is to maximize generic concepts and minimize technology-specific knowledge inside the Kernel.

---

# Incremental Architecture Validation Principle

## Principle

A target architecture is not validated by its documentation alone.

It is validated when it can be reached through a sequence of small, atomic, reversible changes while keeping the system operational after every step.

## Rationale

Large architectural rewrites introduce unnecessary risk because the system remains unvalidated until the very end.

AIStack favors incremental architectural evolution.

Each architectural step shall:

- preserve operational behavior;
- compile independently;
- be validated using a real production workflow;
- be committed atomically;
- leave the repository in a releasable state.

## Validation Example

The first Kernel Migration demonstrated this principle.

Generic concepts (Catalog, Catalog View, Selection, Selection Engine, Selection Strategies, Contracts and Kernel Context) were progressively extracted into the Kernel through a sequence of atomic migrations.

After every migration step, the real Music -> Syncthing workflow continued to operate without regression.

This validates that the Knowledge Operating System architecture can emerge incrementally while preserving a continuously functional system.

This migration constitutes the first practical demonstration that the AIStack Knowledge Operating System is achievable through continuous architectural evolution rather than disruptive rewrites.

---

# Kernel Bootstrap Principle

## Principle

The Kernel shall bootstrap itself from governed registrations rather than explicit technology-specific wiring.

Application code should request a configured Kernel Context rather than manually instantiating providers, policies, generators or renderers.

## Rationale

A Knowledge Operating System should be extended by registering new capabilities, not by modifying the Kernel itself.

The Kernel is responsible for assembling governed capabilities.

Individual implementations are responsible only for implementing their contracts.

This separation minimizes coupling while maximizing portability and extensibility.

## Target Architecture

The long-term objective is a Kernel Bootstrap capable of automatically constructing a complete Kernel Context.

The bootstrap progressively loads and registers governed capabilities such as:

- Knowledge Providers;
- Knowledge Policies;
- Knowledge Generators;
- Knowledge Renderers;
- Catalog Views;
- Selection Strategies;
- future Kernel extensions.

Application code should ideally require only:

    ctx = KernelBootstrap.default()

or:

    ctx = KernelContext.load()

The remainder of the system should discover its capabilities through governed registries.

## Validation

The introduction of ProviderRegistry and the first default KernelContext demonstrates the first step toward this architecture.

DockerProvider is no longer instantiated directly by application code.

Instead, applications request a configured Kernel Context which exposes registered providers through governed registries.

This validates the transition from technology wiring toward Kernel-managed capability discovery.
