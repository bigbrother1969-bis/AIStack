---
artifact:
  id: ARCH-0010
  title: Macro-Architecture
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Accepted
  owner: Architecture
  created: 2026-07-24
  updated: 2026-11-17
---

# ARCH-0010 — Macro-Architecture

## Provenance

Version 1.1 left `main` on 2026-10-10 and is at the tag
`archive/heritage-2.0.0-rc1` under `docs/01-architecture/concepts/`. This
version returns with lot 5 of the reintegration (`ADR-0027` § 5). Sections 1 to
9 are version 1.1 unchanged: they are the architecture AIStack is built toward.
§ *Status, 2026-11-17*, at the end, says what `main` holds of it.

## Purpose

Provide a global mental model of AIStack architecture.

------------------------------------------------------------------------

## 1. Vision

AIStack is a Knowledge Operating System designed to build, govern,
explain and transfer the heritage of digital infrastructures.

The primary asset is not software execution.

The primary asset is governed knowledge.

------------------------------------------------------------------------

## 2. Global Architecture

``` mermaid
flowchart TD

    User[Provider / CLI / API]

    Kernel[Kernel<br/>Library Building]

    Runtime[KernelRuntime<br/>Librarian]

    Services[KernelServices]

    Knowledge[Knowledge Service]
    Transport[Transport Service]
    Transaction[Transaction Service]
    Context[Context Service]
    Observation[Observation Service]

    Catalog[Catalog]
    Location[Location Repository]
    Repositories[Repositories]

    Artifacts[Knowledge Artifacts]

    User --> Kernel
    Kernel --> Runtime
    Runtime --> Services

    Services --> Knowledge
    Services --> Transport
    Services --> Transaction
    Services --> Context
    Services --> Observation

    Knowledge --> Catalog
    Knowledge --> Artifacts

    Artifacts --> Repositories
    Artifacts --> Location

    Transport --> Location
    Transport --> Repositories
```

------------------------------------------------------------------------

## 3. Kernel Model

Core principle:

> The Kernel is not the librarian. The Kernel is the library.

The Kernel is responsible for:

-   composition;
-   global state;
-   registries;
-   capability organization.

The Kernel does not execute domain operations.

------------------------------------------------------------------------

## 4. KernelRuntime

KernelRuntime is the librarian.

Responsibilities:

-   receive intents;
-   identify required capabilities;
-   orchestrate service interactions;
-   coordinate execution flow.

KernelRuntime does not replace specialized services.

------------------------------------------------------------------------

## 5. KernelServices

KernelServices are specialized teams of the library.

Example:

``` text
KernelServices

├── KnowledgeService
├── TransportService
├── TransactionService
├── ContextService
├── ObservationService
└── ...
```

Each service:

-   owns its domain;
-   exposes contracts;
-   evolves independently.

------------------------------------------------------------------------

## 6. Knowledge Model

``` text
Knowledge Artifact

        |
        v

Catalog

        |
        v

Location

        |
        v

Repository
```

A Knowledge Artifact contains:

-   identity;
-   provenance;
-   ownership;
-   lifecycle;
-   integrity information;
-   history.

------------------------------------------------------------------------

## 7. Context Bundle

The Context Bundle is a portable snapshot of governed knowledge.

It enables:

-   knowledge transmission;
-   bootstrap;
-   self-onboarding;
-   context reconstruction.

The Context Bundle is not the SPOT.

The repository remains the source of truth.

------------------------------------------------------------------------

## 8. Transport Model

The Transport Service does not transport raw files.

It transports Knowledge Artifacts between Locations.

``` text
Artifact
   |
   v
Location
   |
   v
Transport
   |
   v
Destination Repository
```

------------------------------------------------------------------------

## 9. Architectural Evolution

This document is intentionally maintained as a C2 architecture overview.

Future decisions may produce:

-   ADRs;
-   service contracts;
-   implementation constraints.

Historical conversation analysis must validate final architectural
decisions before promoting concepts into permanent architecture
decisions.

------------------------------------------------------------------------

## Status, 2026-11-17

Measured on `main` at `b10a596`. Sections 1 to 9 describe a target; this says
how far the code is from it.

| Element of § 2 and § 5 | In `main` |
|---|---|
| Kernel | built: the composition of registries and services (`ARCH-0002`) |
| KernelRuntime | built: resolves a Request to a Task, executes it, keeps the trace |
| Transport Service | built: `KernelServices.transport` |
| Transaction Service | built: `KernelServices.transactions` |
| Execution (trace repository) | built: `KernelServices.execution`, not in the list of § 5 |
| Knowledge Service, Context Service, Observation Service | **not built** |
| Context Bundle (§ 7) | **not in `main`**: at the tag, returns with lot 8 |

`KernelServices` holds three services today, not the five of the diagram. The
three that do not exist are not planned by this document: each would be
built the day a case needs it (`ARC-P-006`).
