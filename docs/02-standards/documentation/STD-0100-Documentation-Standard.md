---
artifact:
  id: STD-0100
  title: Documentation Standard
  type: Documentation Standard
  status: Published
  version: 1.0
  owner: Foundation
  created: 2026-07-06
  updated: 2026-07-06

relations:
  references:
    - STD-0001
    - FDN-0004
    - FDN-0005
---

# STD-0100 — Documentation Standard

## Purpose

This standard defines the canonical structure of every Knowledge Artifact produced within AIStack.

Its objective is to ensure consistency, traceability, readability and long-term maintainability.

---

# Scope

This standard applies to every canonical document stored in the AIStack Git repository.

Examples include:

- Foundation Documents
- Standards
- Architecture Documents
- ADRs
- Component Documentation
- Policies
- Reports

---

# Mandatory Metadata

Every Knowledge Artifact shall begin with a governance metadata block.

The metadata shall include at least:

- identifier
- title
- artifact type
- status
- version
- owner
- creation date
- last update date

Optional metadata may include:

- reviewers
- approval date
- tags
- related components

---

# Mandatory Structure

Every document shall follow the same high-level organization.

1. Metadata
2. Title
3. Purpose
4. Scope
5. Content
6. Related Artifacts

Additional sections may be added when appropriate.

---

# Writing Principles

Documentation shall:

- be written in English;
- use explicit terminology;
- avoid ambiguity;
- remain technology-independent whenever possible;
- preserve understanding before describing implementation.

---

# Traceability

Every document shall expose its governance explicitly.

Knowledge shall never rely solely on Git history.

Governance metadata are part of the Knowledge Artifact itself.

---

# Cross References

Whenever possible, documents shall reference other Knowledge Artifacts by their identifier.

Example:

- FDN-0005
- STD-0001
- ADR-0001
- CMP-0001

References should remain stable even if document titles evolve.

---

# Generated Artifacts

Generated artifacts are disposable.

Corrections shall always be applied to:

- the canonical Knowledge Artifact;
- the generator;
- or the generator configuration.

Generated documents shall never become the Single Point of Truth.

---

# Compliance

A document is considered compliant when:

- governance metadata are present;
- mandatory sections exist;
- identifiers follow the naming convention;
- cross references use canonical identifiers.

---

# Related Artifacts

- STD-0001 — Standards
- FDN-0004 — Governed Heritage
- FDN-0005 — Project Operating Modely

