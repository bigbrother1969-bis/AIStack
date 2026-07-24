# AIStack Macro-Architecture

## Status

-   Type: C2 --- Architecture Overview
-   Status: Reference concept --- Pending architecture consolidation
-   Purpose: Provide a global mental model of AIStack architecture.

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
