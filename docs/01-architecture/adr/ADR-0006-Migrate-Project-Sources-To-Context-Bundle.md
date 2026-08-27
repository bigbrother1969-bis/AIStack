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
  version: 1.1
  created: 2026-07-24
  updated: 2026-08-27
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

## Implementation state

Measured 2026-08-27. **All five steps of § *Migration Strategy* are done**, and
this is the first of the eight silent decisions where the measurement found
nothing outstanding.

| Step | State |
|---|---|
| 1 — Context Bundle pipeline implementation | done — 2026-08-27 |
| 2 — Export validation | done — 2026-08-27 |
| 3 — Legacy compatibility tests | done — 2026-08-27 |
| 4 — Replace legacy implementation by service call | done — 2026-08-27 |
| 5 — Remove obsolete generation logic | done — 2026-08-27 |

What each was read against:

| Step | Evidence |
|---|---|
| 1 | `context_bundle/engine.py`, and `discovery/`, `builders/`, `registry/`, `export/` beside it |
| 2 | `tests/integration/context_bundle/export/` — full export, manifest in zip, readme in zip — with `test_context_bundle_pipeline.py`, `test_contract_inventory_travels.py`, `test_identity_survives_the_projection.py` |
| 3 | `tests/integration/context_bundle/legacy/test_legacy_export_compatibility.py`, which runs the real script as a subprocess and asserts the archive and its README exist |
| 4 | `scripts/export_project_sources.py`, line 269: it constructs `DefaultContextBundleService` and calls `service.generate(...)` |
| 5 | that script defines five functions — `git_commit`, `is_publishable_url`, `declared_repository_url`, `repository_url`, `main` — and none of them generates or packages anything |

**Step 3 has a property worth stating, because the publication procedure rests
on it.** That test runs the real exporter against the real repository, so a
suite run **regenerates the projection**. It is why `pytest -q` followed by
`python3 -m aistack.cli.knowledge_integrity` — the order OPS-0002 § 1
prescribes — reports on the working tree rather than on whatever was last
generated.

### This decision is what supersedes ADR-0005's fourth row

ADR-0005 § *Migration* asks for the exporter to become *a lower-level source
collection component*. **This decision, accepted later, says something else in
its own § *Decision*:**

> `python3 scripts/export_project_sources.py` is the official Context Bundle
> generation entry point. It invokes the Context Bundle service and the
> configured transport layer.

So the script staying an entry point that calls the service is not what
happened *instead* of a plan — it is what a later accepted decision decided.
ADR-0005 v1.2 recorded that row as `superseded` on 2026-08-27 and gave the
reason as *obtained by another route*, which was measured from the code alone.
The reason is this artifact, and ADR-0005 v1.3 says so.

*That gap is the third measurement of GOV-0002/OS-001, missed again: what
implements a decision, what consumes it, and **what governs it**. The first two
were taken and the third was not, on the same day the register recorded that
any one alone gives a confident wrong answer.*

## Principles Applied

-   Knowledge is the primary asset.
-   Every knowledge artifact has a SPOT.
-   Generated artifacts are disposable.
-   Architecture before implementation.
-   Tests are mandatory at every layer.
-   Backward compatibility during migration.
