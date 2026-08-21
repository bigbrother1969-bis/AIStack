---
artifact:
  id: ADR-0006
  owner: Architecture
  status: Accepted
  title: Migrate Project Sources Export To Context Bundle
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
---

# ADR-0006 - Migrate Project Sources Export To Context Bundle

## Status

Accepted

## Context

AIStack historically used `scripts/export_project_sources.py` to
generate a portable project source bundle.

The legacy implementation handled file discovery, validation, exclusion
rules, Markdown generation and ZIP creation directly.

This mixes knowledge discovery, knowledge modeling, rendering and
transport.

The Context Bundle must become a governed knowledge artifact generated
through the AIStack knowledge pipeline.

## Decision

The legacy exporter is migrated to the Context Bundle architecture.

New flow:

    Source Repository
            |
            v
    Knowledge Discovery
            |
            v
    Knowledge Artifacts
            |
            v
    Knowledge Registry
            |
            v
    Context Bundle
            |
            v
    Bundle Export Manager
            |
            +--> JSON
            +--> Markdown
            +--> ZIP

`python3 scripts/export_project_sources.py` is the official Context Bundle generation entry point.

It invokes the Context Bundle service and the configured transport layer.

## Rationale

This provides:

-   separation between knowledge and representation;
-   a Single Point Of Truth for exported knowledge;
-   reusable generation capabilities;
-   explainable and testable pipelines.

## Migration Strategy

1.  Context Bundle pipeline implementation.
2.  Export validation.
3.  Legacy compatibility tests.
4.  Replace legacy implementation by service call.
5.  Remove obsolete generation logic.

## Principles Applied

-   Knowledge is the primary asset.
-   Every knowledge artifact has a SPOT.
-   Generated artifacts are disposable.
-   Architecture before implementation.
-   Tests are mandatory at every layer.
-   Backward compatibility during migration.
