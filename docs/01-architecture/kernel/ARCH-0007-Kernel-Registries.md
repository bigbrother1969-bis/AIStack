---
artifact:
  id: ARCH-0007
  title: Kernel Registries
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 2.0
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-11-17
---

# ARCH-0007 — Kernel Registries

## Provenance

Version 1.4 left `main` on 2026-10-10 and is at the tag
`archive/heritage-2.0.0-rc1` under `docs/01-architecture/kernel/`. This version
returns with lot 5 of the reintegration (`ADR-0027` § 5). The inventory below
was measured on `main` at `b10a596`; the long account of the `PipelineRegistry`
that never existed stays at the tag.

## Purpose

This document describes Kernel registries and governed capability discovery.

## Responsibility

Registries expose Kernel capabilities without hardcoding technology-specific behavior into the Runtime.

## Current Registries

Five classes derive from `aistack.kernel.registry.Registry[T]`:

| Registry | What it holds | On the Kernel | Registered at bootstrap |
|---|---|---|---|
| `ProviderRegistry` | Knowledge Providers | `registries.providers` | `docker`, `compose`, `storage`, `backup`, `gpu`, `host` |
| `CatalogViewRegistry` | Catalog View engines | `registries.catalog_views` | `music-selection`, `docker-containers`, `media-tree` |
| `SelectionStrategyRegistry` | Selection Strategies | `registries.selection_strategies` | none, on purpose |
| `TaskRegistry` | executable Tasks | `registries.tasks` | `health.render`, `architecture.render`, `console.render`, `timemachine.rebuild`, `network_docker.discover`, `ai.reason` |
| `ContractRegistry` | official Kernel contracts, keyed by class name | **not on the Kernel** | — |

`KernelRegistries` aggregates the first four. `ContractRegistry` is exported
by `aistack.kernel.registries` and composed into nothing: its only consumer is
`tests/unit/kernel/test_contract_registry.py`. It is listed because it exists,
and marked because a registry the Kernel does not carry cannot be discovered
the way § *Discovery Model* describes.

There is no pipeline registry. A knowledge chain is a Task (`ARCH-0002`).

## Discovery Model

Capabilities are registered into the Kernel during bootstrap, and only from
`src/aistack/registrations.yml`: a provider, a catalog view or a task is a
line there, built by its factory with no argument.

Application code asks the Kernel for a provider instead of instantiating it
(`ADR-0027` § 9). A chain reads through the providers of the Kernel that runs
it; a function called alone boots one for the occasion.

One case is built where it is used and never registered: a provider whose
constructor takes something supplied per use — a URL, credentials, a
filesystem root, a network range. It follows its caller, which is a Task
(`ADR-0027` § 4); `scripts/ghe_audit.py` counts those that are not yet one.

## Principle

The Kernel is extended by registration, not by modification.
