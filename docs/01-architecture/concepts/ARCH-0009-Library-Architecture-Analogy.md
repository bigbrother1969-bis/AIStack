---
artifact:
  id: ARCH-0009
  title: Library Architecture Analogy
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-07-24
  updated: 2026-08-21
---

# ARCH-0009 — Library Architecture Analogy

## Status

-   Type: C1 --- Concept / Conceptual Model
-   Status: Validated concept --- Pending architecture consolidation

## Purpose

Provide a shared mental model for AIStack architecture.

AIStack can be understood as a governed digital library.

## Core principle

The Kernel is not the librarian.

The Kernel is the library building.

The Kernel owns the structure, composition and global state, but it does
not execute business activities.

The KernelRuntime is the librarian.

It receives requests, identifies the required capabilities, and
orchestrates interactions between specialized services.

## Mapping

  -----------------------------------------------------------------------
  Library                 AIStack                 Responsibility
  ----------------------- ----------------------- -----------------------
  Building                Kernel                  Hosts and organizes the
                                                  system

  Library map             KernelRegistries        Locates capabilities
                                                  and services

  Librarian               KernelRuntime           Orchestrates operations

  Specialized teams       KernelServices          Independent domain
                                                  services

  Acquisition department  KnowledgeService        Manages Knowledge
                                                  Artifacts

  Logistics department    TransportService        Moves artifacts between
                                                  locations

  Administration          TransactionService      Guarantees traceability
                                                  and consistency

  Storage rooms           Repositories            Store artifacts

  Catalog                 Catalog                 Describes the heritage

  Shelf references        Location                Identifies artifact
                                                  location

  Books                   Knowledge Artifacts     The knowledge heritage

  Reader                  Provider / CLI / API    Expresses intent
  -----------------------------------------------------------------------

## Architectural consequence

AIStack architecture should separate:

### Kernel

-   composition
-   state
-   registries

### KernelRuntime

-   orchestration

### KernelServices

-   specialized capabilities
-   independent evolution

## Future evolution

This concept may later produce:

-   architecture decisions (ADR)
-   kernel responsibility documentation
-   KernelServices contracts
-   implementation guidelines

This artifact is intentionally maintained as a C1 concept until
historical conversation analysis validates final architectural
decisions.
