---
artifact:
  id: ARCH-0007
  title: Kernel Registries
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-08-28
---

# ARCH-0007 — Kernel Registries

## Purpose

This document describes Kernel registries and governed capability discovery.

## Responsibility

Registries expose Kernel capabilities without hardcoding technology-specific behavior into the Runtime.

## Current Registries

Measured 2026-08-28. Five classes derive from `aistack.kernel.registry.Registry[T]`:

| Registry | What it holds | On the Kernel Context |
|---|---|---|
| `ProviderRegistry` | Knowledge Providers | `registries.providers` |
| `CatalogViewRegistry` | Catalog View engines | `registries.catalog_views` |
| `SelectionStrategyRegistry` | Selection Strategies | `registries.selection_strategies` |
| `TaskRegistry` | executable Tasks | `registries.tasks` |
| `ContractRegistry` | official Kernel contracts, keyed by class name | **not exposed** |

`KernelRegistries` aggregates the first four. `ContractRegistry` is exported by
`aistack.kernel.registries` and composed into nothing: measured 2026-08-28, its
only consumer in the repository is `tests/unit/kernel/test_contract_registry.py`.
It is listed because it exists, and marked because a registry the Kernel Context
does not carry cannot be discovered the way § *Discovery Model* below describes.

**This section listed a `PipelineRegistry` and it exists nowhere** — no class, no
module, no package, measured across the repository on 2026-08-28 with `archive/`
excluded. It was removed rather than kept as an intention: the section is called
*Current* and a reader takes it as an inventory. `TaskRegistry` and
`ContractRegistry` were absent from a list of four while existing in code, so the
same measurement corrected the list in both directions. The error was found on
2026-08-28 while measuring ADR-0004 § *Consequences*, which names six registries
of which one exists — the two documents were wrong about different registries and
neither checked the other.

*What still asserts a Knowledge Pipeline, per GOV-0002 § What a closure must
carry, rule 2:* **No `Pipeline` type exists** — `KnowledgePipeline` was removed
with `PipelineRegistry` on 2026-08-27 under GOV-0002/OS-001 and qualified
`abandoned`, which is why this section named a registry that had stopped
existing the day before.

ARCH-0005 § *Contract* declared that pair's contract and was corrected on
2026-08-28, on the owner's decision: a Knowledge Pipeline is a named sequence
and not an object, and its § *Current Pipelines* now measures the four commands
that collect from a provider rather than naming two. ARCH-0001 § *Architecture
Map* lists the concept, which ARCH-0005 keeps and defines. **ARCH-0002 § *Core
Components* still lists it among components**, which under that definition it is
not; left to ARCH-0002 rather than corrected from here.

## Discovery Model

Capabilities are registered into the Kernel Context during bootstrap.

Application code requests capabilities from the Kernel Context instead of instantiating implementations directly.

## Principle

The Kernel is extended by registration, not by modification.
