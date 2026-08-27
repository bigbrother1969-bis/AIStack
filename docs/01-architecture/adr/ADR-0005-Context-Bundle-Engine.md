---
artifact:
  id: ADR-0005
  title: Context Bundle Engine Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Accepted
  owner: Architecture
  created: 2026-07-24
  updated: 2026-08-27
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

### Re-measured 2026-08-27

| Step | State |
|---|---|
| `ContextBundleEngine`, and `DefaultContextBundleEngine` orchestrating discovery → artifact building → registry → bundle → export | done — 2026-08-27 |
| Each stage behind an injectable contract | done — 2026-08-27 |
| The engine replaces the exporter as the governed packaging layer | done — 2026-08-27 |
| The exporter becomes a lower-level source collection component | superseded — 2026-08-27 |

**The third bullet above is false, and it was false when this section was
re-read.** It says the migration has not happened. It has.

`scripts/export_project_sources.py`, measured 2026-08-27:

```python
service = DefaultContextBundleService(
    transfer_service=transfer_service,
    measure_contracts=take_inventory,
)
bundle = service.generate(
    source_path=ROOT, output_path=OUTPUT,
    source_commit=git_commit(), repository_url=repository_url(),
)
```

The script packages nothing. No `ZipFile`, no `bundle.md`, no manifest — it
resolves the commit and the repository URL, loads the transfer configuration,
calls the service, and writes the companion README. Everything else is inside
the engine, and `MarkdownDiscovery` does the source collection.

**The bullet is kept rather than rewritten**, under the date it was observed.
It was true on 2026-08-21 and stopped being true without anyone re-reading it,
which is the condition STD-0100 § *An assertion about the code carries its
date* exists for — and which no check here catches, because the sentence
carries no marker: *has not happened* is not *not yet*.

### Why the last row is `superseded` and not `done`

§ *Migration* asks for two things, and only the first happened as written.

The second expected the script to survive **inside** the engine, as a
component the engine calls to collect sources. What happened is the reverse:
**the script calls the engine.** Collection did leave the script — it is
`MarkdownDiscovery`'s, in the engine — so what the step was for is true. The
route is not the one the sentence described, and the script is not a component
of anything: it is an entry point that configures and calls.

**Decided 2026-08-27 by the owner:** obtained by another route, closed.
Forcing the script to become an internal brick would add a layer so that the
code matches a sentence.

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
