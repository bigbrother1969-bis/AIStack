---
artifact:
  id: STD-0001
  title: Standards
  type: Standard Domain
  status: Published
  version: 1.0
  owner: Foundation
  created: 2026-07-06
  updated: 2026-07-06

relations:
  references:
    - FDN-0003
    - FDN-0004
    - FDN-0005
---

# STD-0001 — Standards

## Purpose

This document introduces the Standards domain.

Standards transform Foundation principles into operational engineering practices.

They define how Governed Knowledge is documented, structured, identified and maintained throughout the AIStack project.

---

# Relationship with Foundation

Foundation defines the principles.

Standards define how these principles are applied consistently.

Standards never redefine Foundation concepts.

---

# Scope

The Standards domain governs:

- documentation standards
- specification standards
- naming conventions
- writing rules
- Knowledge Artifact Types
- document templates

---

# Hierarchy

The Standards domain follows the hierarchy below.

```text
Foundation
        ↓
Standards
        ↓
Knowledge Artifact Types
        ↓
Templates
        ↓
Knowledge Artifacts
```

---

# Standards

Standards define mandatory engineering rules.

Every contributor shall follow published standards unless an approved Architecture Decision Record specifies otherwise.

---

# Conventions

Conventions describe recommended practices.

They improve consistency but are not mandatory.

---

# Knowledge Artifact Types

A Knowledge Artifact Type (KAT) defines the canonical structure of a category of Knowledge Artifacts.

Examples include:

- Foundation Documents
- Component Specifications
- ADRs
- Architecture Documents
- Testing Documents

---

# Templates

Templates are practical implementations of Knowledge Artifact Types.

They provide contributors with reusable document structures.

Templates are derived from Standards.

---

# Governance

Every standard is a governed Knowledge Artifact.

Each standard has:

- an identifier
- an owner
- a lifecycle
- a version
- explicit relationships

---

# Future Evolution

The Standards domain is expected to evolve continuously as AIStack matures.

Standards should remain stable while templates may evolve more frequently.

---

# Related Artifacts

- FDN-0003 — Constitution
- FDN-0004 — Governed Heritage
- FDN-0005 — Project Operating Model
