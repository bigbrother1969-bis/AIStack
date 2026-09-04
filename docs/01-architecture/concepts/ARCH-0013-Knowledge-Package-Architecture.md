---
artifact:
  id: ARCH-0013
  title: Knowledge Package Architecture
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Draft
  owner: Architecture
  created: 2026-07-25
  updated: 2026-09-03
---

# ARCH-0013 — Knowledge Package Architecture

## Status

-   Category: C2 Architecture Principle
-   Source:
    AIStack-Knowledge-Package-Governance-Architecture-Principles-Batch.md
-   Purpose: Define the architecture governing knowledge package
    transport, validation and integration.

This document is the governed architecture location for Knowledge
Package principles.

------------------------------------------------------------------------

# Knowledge Package Is a Transport Container

A KnowledgePackage is a temporary container used to transport Knowledge
Artifacts between environments.

A KnowledgePackage is not a Single Point Of Truth.

The repository remains the SPOT.

Flow:

``` text
Knowledge Repository
        |
        v
KnowledgePackage
        |
        v
Target Environment
```

------------------------------------------------------------------------

# PackageManager Is a Capability-Orchestrating Facade

The PackageManager coordinates knowledge package operations.

Responsibilities:

-   Receive Knowledge Packages.
-   Inspect package content.
-   Resolve available capabilities.
-   Orchestrate validation and integration workflows.

The PackageManager does not replace governance decisions.

------------------------------------------------------------------------

Profiles Operationalize Policies

Principle

A Profile is an operational contract consumed by an Engine.

A Profile is not a Single Point Of Truth (SPOT).

The governing SPOT always remains the applicable Knowledge Policies.

A Profile defines the operational requirements applicable to a specific Knowledge Artifact or Knowledge Package, including:

required Capabilities;

compatibility constraints;

validation requirements;

security requirements;

packaging requirements;

operational constraints.

A Profile may be resolved in two ways.

Policy-Based Profile (default)

By default, a Profile is derived from the applicable Knowledge Policies.

Knowledge Policies
        │
        ▼
     Profile
        │
        ▼
      Engine

Policies govern the requirements.

The Profile exposes those requirements as an operational contract.

The Engine consumes the Profile without redefining or interpreting the governing Policies.

Custom Profile (exception)

A Profile may also be explicitly supplied for a specific operation.

A Custom Profile is used when the default Policy-based resolution does not represent the intended operational requirements.

A Custom Profile shall remain:

explicit;

traceable;

validated;

limited to the operation for which it was supplied.

A Custom Profile does not replace or modify the governing Knowledge Policies.

Profile Types

This document distinguishes two Profile types.

Artifact Profile

Defines the operational requirements applicable to a Knowledge Artifact.

Package Profile

Defines the operational requirements applicable to a Knowledge Package.

The Package Profile determines, among other things:

required Capabilities;

compatibility constraints;

validation requirements;

transport requirements.

Architectural Rule

Knowledge Policies
        │
        ▼
     Profiles
        │
        ▼
      Engines
        │
        ▼
   Capabilities

Knowledge Policies govern.

Profiles operationalize.

Engines execute.

Capabilities implement.

Engines shall consume resolved Profiles.

Engines shall never embed Policy resolution or Profile definition inside their business logic.

------------------------------------------------------------------------

# Separation Between Axioms, Concepts, Engines and Adapters

AIStack architecture separates:

``` text
Axioms
   |
   v
Concepts
   |
   v
Engines
   |
   v
Adapters
```

Responsibilities:

-   Axioms define immutable principles.
-   Concepts define the governed knowledge model.
-   Engines implement deterministic processing.
-   Adapters connect external technologies.

------------------------------------------------------------------------

# Engines Manipulate Concepts, Not Axioms

Engines must operate on governed concepts.

They must not directly manipulate foundational principles.

This preserves architecture stability.

------------------------------------------------------------------------

# Adapters Implement Capabilities

Adapters provide concrete implementations of governed capabilities.

Adapters remain replaceable.

The architecture must not depend on a specific technology adapter.

------------------------------------------------------------------------

# Registries Govern Discovery, Repositories Store Artifacts

Registries and repositories have different responsibilities.

Registry:

-   Discovery.
-   Indexing.
-   Classification.
-   Governance metadata.

Repository:

-   Storage.
-   Preservation.
-   Versioning of artifacts.

------------------------------------------------------------------------

# Validation and Integration Are Separate Responsibilities

Validation determines whether a proposed integration is acceptable.

Integration applies validated changes.

Flow:

``` text
KnowledgePackage
        |
        v
ValidationEngine
        |
        v
IntegrationEngine
        |
        v
Knowledge Heritage
```

Validation and integration must remain separate capabilities.

------------------------------------------------------------------------

# Knowledge Package Lifecycle

A KnowledgePackage follows a governed lifecycle:

``` text
Creation
   |
   v
Transport
   |
   v
Inspection
   |
   v
Validation
   |
   v
Integration
   |
   v
Archive
```

A package is a temporary transport artifact.

The integrated knowledge becomes part of the governed heritage.

------------------------------------------------------------------------

# Open Points

Future architecture work must define:

-   Exact PackageManager interfaces.
-   Validation policies.
-   Integration conflict resolution rules.
-   Package version lifecycle management.

------------------------------------------------------------------------

# Status, 2026-09-03

`status: Draft` stays, decided rather than merely carried forward —
`GOV-0002/OS-051`. `FDN-0002` (the Glossary) cites this document as the
declared SPOT of two terms, *Adapter* and *Profile*, while it is Draft;
the question of whether that should change was named on 2026-08-29 and
left unasked until now. The four items in § *Open Points* above are the
answer: they are unresolved architecture, not an administrative gap, and
promoting this document to `Accepted` would assert they are settled when
they are not. Two Glossary entries defer to a Draft SPOT anyway, and
continue to — the reasoning above is why, dated rather than left as an
open question each reader has to re-derive.
