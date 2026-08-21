---
artifact:
  id: ADR-0005
  title: Context Bundle Engine Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Accepted
  owner: Architecture
  created: 2026-07-24
  updated: 2026-08-21
---

# ADR-0005 --- Context Bundle Engine Architecture

## Status

Accepted.

`Proposed` until 2026-08-21, which described neither the decision nor the
code. The decision had been taken and largely carried out; see
*Implementation state*.

## Implementation state

Observed on 2026-08-21, at `90313d6`:

- `DefaultContextBundleEngine` exists in
  `src/aistack/context_bundle/engine.py` and orchestrates the pipeline this
  ADR describes: discovery, artifact building, registry building, bundle
  building, export.
- Each stage sits behind a contract in `src/aistack/contracts/`, and each is
  injectable — the engine coordinates and does nothing else.
- **The migration below has not happened.** `scripts/export_project_sources.py`
  is still the entry point every operator and every published command uses;
  the engine has not replaced it as the governed packaging layer. The
  exporter has not become a lower-level source collection component either —
  it does the packaging itself.

The decision stands. One step of it remains.

## Context

The current AIStack project source export mechanism produces a portable
archive of repository files.

However, a Knowledge Operating System requires more than source
transportation.

AIStack needs a Context Bundle capable of representing its complete
governed knowledge heritage in a portable and explainable form.

The Context Bundle must contain the complete knowledge corpus.

Classification and criticality must not be used to filter knowledge.

They must define how AI systems interpret and use knowledge.

## Decision

AIStack introduces a Context Bundle Engine.

The Context Bundle Engine is responsible for generating a complete
portable representation of AIStack governed knowledge.

The bundle is composed of:

-   knowledge artifacts;
-   provenance metadata;
-   classification metadata;
-   criticality metadata;
-   generation metadata.

## Fundamental Principles

### Complete Heritage

A Context Bundle contains the complete governed knowledge heritage
required to rebuild AIStack context.

Knowledge inclusion and knowledge usage are separate concerns.

### Classification Is Semantic

Knowledge classification defines:

-   the domain;
-   the semantic type;
-   the relationship between artifacts.

The official domains are:

-   Foundation;
-   Architecture;
-   Governance;
-   Standards;
-   Engineering;
-   Knowledge Assets.

### Criticality Defines AI Behavior

Criticality does not define whether knowledge is included.

Criticality defines how AI systems must treat knowledge.

C3:

-   preserve;
-   never contradict;
-   require validation before modification.

C2:

-   respect;
-   maintain traceability;
-   justify evolution.

C1:

-   use as guidance;
-   adapt when context requires.

## Target Architecture

Repository

↓

Knowledge Discovery

↓

Knowledge Artifact Model

↓

Classification

↓

Criticality Assignment

↓

Context Bundle

↓

Portable Knowledge Heritage

## Consequences

Positive:

-   complete portability;
-   explainable AI behavior;
-   deterministic reconstruction;
-   separation between knowledge storage and knowledge usage.

Negative:

-   additional metadata management;
-   more explicit governance requirements.

## Migration

The existing project source exporter becomes a lower-level source
collection component.

The Context Bundle Engine replaces it as the governed packaging layer.
