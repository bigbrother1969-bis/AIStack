# Kernel Runtime Roadmap

## Purpose

This document tracks the implementation roadmap of the AIStack Kernel Runtime.

It complements the Runtime architecture documentation.

The Runtime README describes the architecture.

This roadmap describes the implementation workstreams.

---

# Current Development Phase

The current priority is to implement the deterministic Runtime operations.

Implementation order:

1. boot
2. discover
3. catalog
4. view
5. select
6. evaluate
7. generate
8. render
9. export_bundle
10. run

Each operation shall become a governed Runtime capability with explicit contracts, lifecycle states and traceability.

---

# Validation Workstreams

## Workstream 1

Improve Technical Debt Score.

Objective:

Demonstrate deterministic knowledge evaluation followed by AI-assisted reasoning.

---

## Workstream 2

Restart Convergence Monitoring.

Objectives:

- monitor server restart convergence;
- detect blocked, zombie and orphan containers;
- distinguish transient from confirmed failures;
- recover automatically until convergence;
- expose the complete convergence history.

---

## Workstream 3

Generic Docker Compose Discovery.

Objectives:

- automatically discover compose projects;
- remove Gigabyte/Raspberry-specific assumptions;
- support arbitrary infrastructures;
- rely primarily on deterministic discovery mechanisms.

---

## Workstream 4

AI Knowledge Grounding.

Objectives:

- ingest Context Bundles;
- ingest generated documentation;
- build governed AI knowledge;
- preserve provenance;
- preserve traceability;
- keep Git as the Single Point Of Truth;
- keep AI engines replaceable.

---

# Future Work

After completion of the Runtime validation workstreams, AIStack will begin implementing multi-orthogonal history.

The objective is to introduce four complementary historical dimensions:

- Heritage History (Git)
- Runtime History (operations)
- Runtime State History (lifecycle)
- Knowledge Ledger (knowledge evolution)

These four histories will ultimately enable a future Knowledge Time Machine capable of reconstructing the governed knowledge heritage at any point in time.

This work intentionally starts only after the Runtime foundation is operational.
