---
artifact:
  id: FDN-PRINCIPLES
  title: AIStack Principles Registry
  type: Foundation Registry
  criticality: C3
  version: 1.0
  status: Draft
  owner: Foundation

lifecycle:
  created: 2026-07-24
  updated: 2026-07-24

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0004
---

# AIStack Principles Registry

## Purpose

This document defines the Single Point Of Truth for AIStack principles.

A principle is a stable governed rule used to guide architectural,
governance, engineering or operational decisions.

Principles are classified by:

- domain;
- semantic scope;
- criticality.

Criticality defines how AIStack must behave when using these principles.

---

# Criticality Model

## C3 — Core Principle

A C3 principle defines a fundamental invariant.

AIStack behavior:

- must always preserve the principle;
- must never contradict it;
- changes require explicit validation;
- included in minimal context.

---

## C2 — Governed Principle

A C2 principle defines an important governed rule.

AIStack behavior:

- may evolve through governed change;
- impact must be explained;
- references must remain consistent.

---

## C1 — Operational Principle

A C1 principle defines operational guidance.

AIStack behavior:

- may be adapted;
- can evolve locally;
- does not impact global identity.

---

# Foundation Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| FDN-001 | No AI without Data | C3 |
| FDN-002 | No Data without Governance | C3 |
| FDN-003 | AI is a means, never an end | C3 |
| FDN-004 | Knowledge is the primary engineering asset | C3 |
| FDN-005 | Every knowledge item has a Single Point Of Truth | C3 |
| FDN-006 | Every knowledge item is governed | C3 |
| FDN-007 | Every recommendation is explainable | C3 |
| FDN-008 | Every transformation is traceable | C3 |
| FDN-009 | Architecture comes before implementation | C3 |
| FDN-010 | AIStack applies its principles to itself first | C3 |

---

# Governance Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| GOV-001 | The AI never creates authoritative knowledge | C3 |
| GOV-002 | Every modification is a governed transaction | C2 |
| GOV-003 | Transactions must be atomic, complete and reproducible | C2 |
| GOV-004 | Gravé creates permanent governed knowledge | C2 |
| GOV-005 | Documentation is part of the product | C2 |
| GOV-006 | Knowledge ownership and lifecycle must be explicit | C2 |

---

# Architecture Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| ARC-001 | Generic Kernel Principle | C3 |
| ARC-002 | Kernel Bootstrap Principle | C3 |
| ARC-003 | Runtime and AI responsibilities remain separated | C3 |
| ARC-004 | Technology-specific concepts never belong in the Kernel | C3 |
| ARC-005 | Contracts before implementations | C2 |
| ARC-006 | Earned Abstractions | C2 |
| ARC-007 | Modular Monolith First | C2 |
| ARC-008 | Architecture evolves through incremental validated steps | C2 |
| ARC-009 | Deployment boundaries do not define architecture boundaries | C2 |

---

# Standards Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| STD-001 | Documentation First | C2 |
| STD-002 | Specification before implementation | C2 |
| STD-003 | Official terminology must be preserved | C2 |
| STD-004 | One validated concept, one commit | C2 |
| STD-005 | Naming conventions are governed | C2 |

---

# Engineering Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| ENG-001 | The engineer's role is understanding, not writing code | C2 |
| ENG-002 | Industrial quality is achieved before implementation | C2 |
| ENG-003 | Generated artifacts are disposable | C2 |
| ENG-004 | Improve generators instead of generated artifacts | C2 |
| ENG-005 | Validate every architectural step independently | C2 |
| ENG-006 | Prefer simple modular maintainable solutions | C1 |

Contracts Derive from Policies

Domain: Engineering

Criticality: C2 — Governed Principle

Principle

Contracts are the operational expression of the applicable Policies under a given Profile.

A Contract is never invented by an implementation.

Engineering Chain

Responsibility
    |
    v
Policies
    |
    v
Profiles
    |
    v
Contracts
    |
    v
Verification
    |
    v
Implementation
    |
    v
Validation

Responsibilities

Responsibilities define why a component exists.

Policies define the governed rules.

Profiles determine which Policies apply.

Contracts translate applicable Policies into explicit and verifiable commitments.

Verification demonstrates Contract compliance.

Implementations fulfill Contracts.

Validation demonstrates business value through User Acceptance Tests (UAT).

Architectural Consequences

The implementation is not the source of truth for behavior.

The Contract is.

The Contract itself remains governed by the applicable Policies and Profile.

> **Truncated content.** A sentence beginning *"Different"* was introduced
> already incomplete by commit `685bcc8` (2026-08-01). No copy of it exists
> anywhere in the Governed Heritage. It is recorded as lost rather than
> removed in silence (FDN-0003, Article 12).

---

# Operations Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| OPS-001 | Deployment is Architecture | C2 |
| OPS-002 | Packaging is an architectural concern | C2 |
| OPS-003 | Rollback is mandatory for risky evolution | C1 |
| OPS-004 | Observe before acting | C2 |
