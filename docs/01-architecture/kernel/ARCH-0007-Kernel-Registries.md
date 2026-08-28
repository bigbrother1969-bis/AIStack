---
artifact:
  id: ARCH-0007
  title: Kernel Registries
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
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
carry, rule 2:* ARCH-0001 § *Architecture Map* names them, ARCH-0002 § *Core
Components* says they *execute deterministic knowledge flows*, and ARCH-0005
§ *Current Pipelines* lists a Docker Runtime Pipeline and a Compose Runtime
Pipeline while its § *Contract* says a pipeline exposes an identifier, a name and
a deterministic run operation. **No `Pipeline` type exists.** What runs under
those two names is `aistack.cli.docker_catalog` and `aistack.cli.compose_catalog`
— two `main()` functions calling a provider, a catalog builder and a generator in
order, carrying no identifier, no name and no run operation. Those three sections
are not corrected here: one commit, one concept, and what they raise is a
question for the owner rather than a measurement — whether the Knowledge Pipeline
is an architecture element still to build, or a name for a sequence that already
runs.

## Discovery Model

Capabilities are registered into the Kernel Context during bootstrap.

Application code requests capabilities from the Kernel Context instead of instantiating implementations directly.

## Principle

The Kernel is extended by registration, not by modification.
