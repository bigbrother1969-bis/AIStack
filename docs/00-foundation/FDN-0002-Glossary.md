---
artifact:
  id: FDN-0002
  title: Glossary
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 1.8
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-09-04

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

**This entry is the Single Point Of Truth for what AIStack is**, and
`FDN-0003` § *Closing Statement* states it in the same words. Two other
descriptions circulate in the heritage, and neither is a competing definition —
they answer different questions, which is stated here because nothing stated it
until 2026-08-28:

| Description | Where | What it answers |
|---|---|---|
| *Infrastructure Knowledge Platform (IKP)* | `README.md`, first line | the **category of product** AIStack presents itself as to a reader who has not opened the heritage |
| *Knowledge Operating System* | `ARCH-0010` § *Vision*, `ADR-0004` § *Context* | the **architecture it is built toward**. `FDN-0004` and `FDN-0008` use the term the same way — *the architecture can emerge incrementally*, *the first operational demonstration of* — never as a definition of what AIStack is |

*Recorded because the three coexisted with no declared relation from at least
2026-08-13, when an external boot report raised it (W-13) as a reason two AI
agents could not converge on the same identity. The relation was missing, not
the answer: this entry and the Constitution have agreed since 2026-07-06.*

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

## Evidence

Raw material collected from reality by a Knowledge Provider, carrying no
interpretation.

Evidence is what discovery produces. `ADR-0008` states it as a frozen decision —
*Discovery produces Evidence, never Knowledge* — and `ARC-P-012` cuts the
acquisition chain at that point: a provider collects and concludes nothing.

**Evidence is not an Observation.** The chain is `Reality → Evidence → Evidence
Normalization → Canonical Observations`. Evidence is untyped and shaped by the
technology it came from — *`docker logs` output, collected and not interpreted*,
per `ADR-0009` § 3.1 — and an Observation is the canonical form it takes once
normalized. Defining them as one thing would give this heritage two words for
one concept, which the Purpose above forbids.

*Written 2026-08-28. The word was already used **by this Glossary** — § *Knowledge
Provider*: "They only collect evidence" — and by twelve governed artifacts, with
no definition anywhere. GOV-0002 records it as W-14 of the 2026-08-13 boot
report.*

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

## Service

A composed part of the Kernel that owns a domain, exposes contracts, and evolves
independently of the others. `ARCH-0010` § 5 names the concept *KernelServices*
and states those three properties.

**A Service is not a Knowledge Provider.** A Provider faces the Digital
Ecosystem, collects evidence from it and interprets nothing; a Service faces
inward, is assembled by the Kernel's composition root, and coordinates one
domain of the platform. The two were used side by side across the architecture
with no statement of the difference until 2026-08-28.

*`ARCH-0010` § 5 introduces its list with **Example:** — the services it names
are illustrations rather than a closed set. That is why one of them being
qualified `abandoned` on 2026-08-28 — the Observation Service, `ADR-0008` —
removes an example instead of contradicting the concept.*

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

## Adapter

The component that connects an external technology to a governed capability.

An Adapter implements a capability; it never defines one. It remains
replaceable, and the architecture never depends on a specific adapter.

**Its SPOT is `ARCH-0013 — Knowledge Package Architecture`**, which places the
Adapter as the last of four layers — *Axioms → Concepts → Engines → Adapters* —
and states that Adapters implement capabilities and remain replaceable. This
entry exists so that the term resolves from the Glossary; `ARCH-0013` governs
it.

Measured 2026-08-29: **no class carries the name.** The concept is implemented
at package level — `aistack/transaction/adapters/`, whose
`TransportOperationEngine` adapts the Knowledge Transport Layer to the generic
`OperationEngine` contract — and the Providers play the same role behind
`KnowledgeProvider`. An architectural layer with no class named after it is a
naming fact, not an absence.

*Written 2026-08-29. `ADR-0008` qualified its own row — technical access through
interchangeable Adapters — as `superseded` on 2026-08-28. **That qualification
concerns that decision's mechanism, not the concept**, which `ARCH-0013`
declares as a layer and this entry defines. The two do not contradict each
other, and the distinction is written here because reading either alone
suggests they do.*

---

## SPOT (Single Point of Truth)

The unique authoritative location where a governed knowledge element is defined.

Every governed concept has exactly one SPOT.

---

## Contract

The explicit, governed representation of a concept: what an implementation must
provide, stated once and stated deliberately.

**Its SPOT is `FDN-0011 — Contract-Based Engineering`**, C3 and Published, whose
first principle requires that *every concept is represented by a single,
coherent, explicit and governed contract*, and derives technical debt from
violations of that architecture rather than from code review. This entry exists
so that the term resolves from the Glossary; `FDN-0011` governs it.

In code a contract is a `Protocol` or a class carrying unimplemented abstract
methods, and it is satisfied **structurally** rather than by declaration —
`contract-debt` compares call shapes, and `false-declarations` reports a class
naming a contract it does not satisfy. Both are published at every projection.

*Written 2026-08-28. The concept was governed at C3 since 2026-07-24 and had no
Glossary entry, which is the shape W-13 and W-15 also had: the answer existed
with more authority than the question.*

---

## Technical Debt

Governed knowledge describing the gap between the current state and the desired state of a Digital Ecosystem.

Technical Debt is derived knowledge.

It is produced from observations, explicit rules, evidence and documented policies.

---

## Knowledge Policy

A governed rule defining how knowledge is evaluated, qualified or interpreted.

Knowledge Policies are explicit and versioned.

**The bare plural *Policies*, used normatively across the heritage, means
Knowledge Policies.** `FDN-0012 § ENG-P-007` — *Contracts derive from Policies*
— and `ARCH-0013`, which makes them the governing SPOT of every Profile, both
mean these. The sentence exists because the word alone does not say so, and a
reader meeting *the applicable Policies* has to guess otherwise.

**There is no governed `Policy` family, and the names are a coincidence of
English.** Measured 2026-08-29: `KnowledgePolicy` declares `name` and
`validate(artifact) -> bool` — a predicate; `BundleTransferPolicy` declares
`enabled` and `target` — a configuration. **They share no member and no base.**
`PackagingPolicy`, defined below in this Glossary, is a third unrelated concept.

*Decided 2026-08-29 by the owner, resolving `GOV-0002/OS-043`. The alternative
was a generic `Policy` entry the others would defer to, which would have made
`PolicyRegistry` — named by `ADR-0004` § Consequences and existing nowhere — a
missing implementation rather than a name that decision happened to write. It
stays the second.*

---

## Profile

An operational contract consumed by an Engine, stating the operational
requirements applicable to a Knowledge Artifact or a Knowledge Package.

**A Profile is never a SPOT.** By default it is derived from the applicable
Knowledge Policies, which remain the governing authority; a Custom Profile may
be supplied for a single operation, and modifies no Policy.

**Its SPOT is `ARCH-0013 — Knowledge Package Architecture`**, which defines the
two resolution modes — Policy-based and Custom — and the two types, *Artifact
Profile* and *Package Profile*. This entry exists so that the term resolves from
the Glossary; `ARCH-0013` governs it.

**`ARCH-0013` is `status: Draft`, and this entry defers to it anyway.** The
alternative was to wait, and waiting has a measured cost: `FDN-0012`, C3 and
Published, already uses the term normatively — *Contracts are the operational
expression of the applicable Policies under a given Profile*. **The word already
governs.** Deferring to a Draft is stated here rather than hidden, so that a
reader knows the ground can move.

**Decided 2026-09-04, `GOV-0002/OS-051`: the ground stays where it is.**
`ARCH-0013` § *Status, 2026-09-04* keeps `status: Draft` on purpose — its
own *Open Points* are unresolved architecture, not an administrative gap —
so this paragraph is not removed by a promotion that was considered and
declined. It stays as the standing statement that this term's SPOT is
Draft and governs anyway.

*Written 2026-08-29, decided by the owner. Measured the same day: 20 of the
term's 24 occurrences in the repository are inside `ARCH-0013`, and no class
carries the name.*

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

**The Context Bundle is the Knowledge Package of AIStack.** Decided
2026-08-29 by the owner. It is the only thing in this heritage that does what
this definition describes: it groups Knowledge Artifacts, declares a
`source_commit` and a `content_hash`, travels, and is explicitly not a SPOT —
`OPS-0002` § *The Context Bundle, and handing one over* governs how one is
produced and handed over.

**Two classes named `KnowledgePackage` were declared in the Kernel and
carried nothing.** Measured 2026-08-29:

```text
kernel/models/knowledge_package.py     KnowledgePackage(id: str)
kernel/knowledge/package.py            KnowledgePackage(identifier: str)
```

Two frozen dataclasses, same name, one field each, differently named, in the
same Kernel — FDN-P-005's subject. Neither was consumed by anything but a
contract with no implementation and a facade returning its argument unchanged.
Both were removed the same day, with `PackageCapability` and `PackageManager`.
**The concept was declared three times and implemented once, under another
name** — the shape `GOV-0002/OS-042` recorded for the Catalog View, a third
time and at the largest scale.

*`ARCH-0013 — Knowledge Package Architecture` is the architectural SPOT of the
concept and is `status: Draft`. This entry does not wait for it: measured
2026-08-29, the term appears in four governed artifacts — this Glossary,
`ARCH-0013`, `ADR-0008` and the register — and the thing it names ships in
every projection while the classes that bore the name did not run at all.*

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
