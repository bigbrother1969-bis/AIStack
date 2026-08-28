---
artifact:
  id: ARCH-0005
  title: Knowledge Pipelines
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

# ARCH-0005 — Knowledge Pipelines

## Purpose

This document describes the Knowledge Pipeline architecture.

## Definition

A Knowledge Pipeline is an executable governed chain that transforms observations into governed Knowledge Artifacts.

## Standard Flow

Provider
  -> Observation
  -> Runtime Catalog
  -> Artifact Generator
  -> Knowledge Artifact

## Current Pipelines

Measured 2026-08-28. Four commands collect from a Knowledge Provider; two of
them execute the flow above end to end, and those two are the pipelines:

| Command | Chain |
|---|---|
| `aistack.cli.docker_catalog` | provider → observation → runtime catalog → artifact generator → artifact |
| `aistack.cli.compose_catalog` | provider → observation → runtime catalog → artifact generator → artifact |
| `aistack.cli.docker_discover` | provider → observation → artifact generator → artifact — **no runtime catalog** |
| `aistack.cli.docker_selection_catalog` | provider → observation → runtime catalog → `DockerSelectionCatalogBuilder` → `json.dumps` — **no artifact generator** |

The two that are not pipelines are named because a list of two that does not say
what it excluded cannot be told from a list nobody re-measured. ARCH-0007
§ *Current Registries* was exactly that until 2026-08-28, and it named a
registry that had been removed the day before.

**The fourth row is the one to read twice.** `docker_selection_catalog` writes
its output with `write_text` and no Artifact Generator, on the same path
GOV-0002/OS-042 records as producing a `SelectionCatalog` where this
architecture expects a Catalog View. Of the four, it is the only one that
crosses none of the governed types of its own chain.

## Contract

**A Knowledge Pipeline is a named sequence, not an object.**

Until 2026-08-28 this section read *a pipeline exposes a pipeline identifier, a
pipeline name and a deterministic run operation*. `KnowledgePipeline` and
`PipelineRegistry` were removed on **2026-08-27** under GOV-0002/OS-001 and
qualified **`abandoned`** — the contract was consumed by exactly one thing, a
registry nothing constructed, not exported by its own package, holding a type
nothing implemented, and removing either alone would have left the other
stranded.

So there is no pipeline type to satisfy, no registry to register into, and no
`run()` to call. What makes a pipeline governed is the chain above: every step
is a contract this heritage declares, and every participant satisfies one. What
a pipeline does not have is an identity of its own, which is why the section
above lists commands rather than names.

*The declaration this replaces survived its own subject by one day. ARCH-0007
named the same removed registry in the same window; two documents described one
absent pair, and neither knew of the other.*

*What still names a Knowledge Pipeline elsewhere, per GOV-0002 § What a closure
must carry, rule 2:* ARCH-0001 § *Architecture Map* lists the concept, which
this document keeps and defines. ARCH-0002 § *Core Components* lists it **among
components**, which under this definition it is not — a named sequence is not a
component. That one is not corrected here: one commit, one concept, and it is a
question about ARCH-0002's own taxonomy rather than about this document.

## Principle

Pipelines make knowledge production executable, repeatable and governable.
