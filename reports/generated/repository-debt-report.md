# Repository Debt Report

Generated: 2026-07-06

---

# Purpose

This report classifies every significant repository element.

It does not modify the repository.

It provides the governed basis for future migration decisions.

---

# Repository Status

| Path | Status | Decision | Notes |
|------|--------|----------|-------|
| docs/00-foundation | ACTIVE | KEEP | Canonical Foundation |
| docs/01-architecture | ACTIVE | KEEP | Architecture documents |
| docs/02-standards | ACTIVE | KEEP | Official standards |
| docs/03-handbook | ACTIVE | KEEP | Reserved |
| docs/04-development | ACTIVE | KEEP | Component documentation |
| docs/04-reference-library | REVIEW | REVIEW | Merge with references |
| docs/adr | REVIEW | MOVE | Integrate into docs/01-architecture/adr |
| docs/glossary | REVIEW | REVIEW | Verify usefulness |
| docs/references | REVIEW | REVIEW | Merge strategy required |

---

# Legacy Components

| Component | Status | Proposed Action |
|----------|--------|-----------------|
| catalog_engine | LEGACY | ARCHIVE |
| generation_engine | LEGACY | ARCHIVE |
| render_engine | LEGACY | ARCHIVE |
| selection_engine | LEGACY | ARCHIVE |
| selection_ui | LEGACY | ARCHIVE |

These components belong to the AIStack V0 prototype.

They remain valuable as engineering heritage.

They should be archived instead of deleted.

---

# Active Components

| Component | Status |
|----------|--------|
| Context Bundle Generator | ACTIVE |
| Foundation | ACTIVE |
| Standards | ACTIVE |

---

# Examples

Status: KEEP

Examples remain useful for demonstrations and future regression testing.

Reorganization may be required later.

---

# Generated Artifacts

Generated artifacts are disposable.

Examples:

- reports/generated
- exports

They are excluded from the Governed Heritage.

---

# Unknown Areas

The following repository elements require manual review.

- history
- source
- docs/glossary
- docs/references
- docs/04-reference-library

No migration shall occur before clarification.

---

# Repository Debt Summary

## Documentation Debt

Medium

Reason:

Legacy documentation structure still coexists with the governed documentation model.

---

## Architecture Debt

Medium

Reason:

Legacy prototype components remain at repository root.

---

## Naming Debt

Low

Reason:

Most canonical Knowledge Artifacts now follow the official naming convention.

---

## Repository Governance Debt

Low

Reason:

Repository Governance document still missing.

---

# Migration Principles

Migration shall respect the Governed Engineering Cycle.

No move without destination.

No deletion without classification.

Archive before delete.

Git remains the Single Point Of Truth.

---

# Next Step

Produce:

FDN-0008 — Repository Governance

before applying repository migration.
