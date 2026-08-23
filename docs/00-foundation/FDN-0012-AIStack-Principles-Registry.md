---
artifact:
  id: FDN-0012
  title: AIStack Principles Registry
  type: Foundation Registry
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 2.3
  status: Draft
  owner: Foundation
  created: 2026-07-24
  updated: 2026-08-23

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0004
---

# AIStack Principles Registry

## Provenance of version 2.2

The renumbering of version 2.0 was incomplete. It left the four Operations
principles — `OPS-001` to `OPS-004` — in the old three-digit form, plus one
citation of `OPS-004` in STD-0300 § 10, sitting on the same line as
`ENG-P-005`. Corrected on 2026-08-22: they are `OPS-P-001` to `OPS-P-004`.

The cause is worth recording, because it is the third instance of one
pattern this week. The renumbering used the expression

```
\b(FDN|STD|GOV|ENG|ARC)-[0-9]{3}\b
```

— a list of prefixes assumed rather than measured. `\b[A-Z]{2,5}-[0-9]{3}\b`
would have found all six families, and is what eventually found the fifth.
An allow list built from assumption, on the task whose entire purpose was to
replace assumption with measurement.

The same shape produced `.dockerignore` patterns that matched only the
context root and a `PYTHONPATH` that declared one of two source roots. Each
looked exhaustive and covered a subset.

**The consequence was not cosmetic.** STD-0102 v2.0 states that the
principle/artifact collision is closed. It was not: `OPS-001` and a future
`OPS-0001` differ by one leading zero, which is precisely the situation the
renumbering was decided to end — and an `OPS-` artifact was under discussion
when the gap was found.

## Provenance of version 2.1

`FDN-P-014 — Technical debt is a property of the contracts, not of the
implementation` was registered on 2026-08-21, when FDN-0011 was engraved.
Until then it was stated in that document and nowhere else, while STD-0300
§ VS-4 already required AIStack to derive technical debt from observations
rather than opinion. The acceptance criteria were governed; the principle
they rest on was not.

**FDN-0011's second principle — *Contract First Engineering* — was
deliberately not registered here.** `ARC-P-005` already says *contracts
before implementations*. The two are the same rule at different altitudes:
one states the ordering, the other states why the ordering follows from
what engineering delivers. Registering both would give one rule two SPOTs,
which FDN-P-005 forbids and which this registry was cleaned of on the same
day. Whether `ARC-P-005` should be reworded to absorb the fuller statement
is an open question, recorded rather than settled.

## Provenance of version 2.0

Every principle was renumbered on 2026-08-21. `FDN-005` became
`FDN-P-005`, and so for all of them: the domain prefix is kept, `P`
is inserted, the three-digit number is kept.

The reason is a measured collision. Principles used three digits and
artifacts four, so fifteen pairs differed by a single leading zero and
named entirely different governed objects:

| principle | artifact |
|---|---|
| `FDN-005` — *every knowledge item has a SPOT* | `FDN-0005` — Project Operating Model |
| `FDN-011` — *evidence produces knowledge* | `FDN-0011` — Contract-Based Engineering |
| `GOV-001` — *the AI never creates authoritative knowledge* | `GOV-0001` — Semantic Knowledge Governance |
| `STD-002` — *specification before implementation* | `STD-0002` — Test Artifact Isolation |

STD-0102 had recorded the weakness and named its own remedy —
architecture had already escaped it by giving documents the `ARCH-`
prefix — while stating plainly that recording it was not fixing it.
`FDN-0011` was registered as an artifact on 2026-08-21, one zero away
from a principle that already existed. That is when a documented
weakness became a live one.

This is a deliberate exception to *"Identifiers never change"*, decided
by the owner on 2026-08-21. It applies to principles only. No artifact
identifier was touched, and no governed file was renamed: the change is
confined to this table and to the places that cite it.

## Provenance of version 1.1

Eight principles were added on 2026-08-21, recovered from
`AIStack-Knowledge-Principles-Consolidated.md` — a hand-maintained
consolidated view that declared itself a *"consolidation draft pending
final historical validation"* and restated forty principles, most of
which already lived here.

Each of the eight was checked against this registry before being added.
The rest of that file held either principles already registered under a
different wording, or *descriptions* of the architecture, which belong to
the `ARCH-` documents and not to a register of principles. The file was
removed once emptied of what only it carried.

**ARC-P-012 deserves a note.** *Providers observe and collect; they never
decide or modify* was violated by `RepositoryProvider`, which assigned
itself `confidence="high"` and `status="observed"` — two values no
governed vocabulary contained. The code was repaired on 2026-08-21,
before the principle it broke had ever been written down. Registering it
now is what makes the repair checkable rather than a matter of taste.

A hand-maintained second view of these principles is not wanted again:
FDN-P-005 gives every knowledge item one Single Point Of Truth, and this
registry is theirs. A consolidated reading, if one is needed, is a
generated projection (ENG-P-003), never a maintained copy.

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
| FDN-P-001 | No AI without Data | C3 |
| FDN-P-002 | No Data without Governance | C3 |
| FDN-P-003 | AI is a means, never an end | C3 |
| FDN-P-004 | Knowledge is the primary engineering asset | C3 |
| FDN-P-005 | Every knowledge item has a Single Point Of Truth | C3 |
| FDN-P-006 | Every knowledge item is governed | C3 |
| FDN-P-007 | Every recommendation is explainable | C3 |
| FDN-P-008 | Every transformation is traceable | C3 |
| FDN-P-009 | Architecture comes before implementation | C3 |
| FDN-P-010 | AIStack applies its principles to itself first | C3 |
| FDN-P-011 | Evidence produces knowledge; discovery never produces knowledge | C3 |
| FDN-P-012 | Every knowledge item is portable across tools, vendors, clouds and models | C3 |
| FDN-P-013 | Historical knowledge is preserved through versions and relationships | C3 |
| FDN-P-014 | Technical debt is a property of the contracts, not of the implementation | C3 |

---

# Governance Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| GOV-P-001 | The AI never creates authoritative knowledge | C3 |
| GOV-P-002 | Every modification is a governed transaction | C2 |
| GOV-P-003 | Transactions must be atomic, complete and reproducible | C2 |
| GOV-P-004 | Gravé creates permanent governed knowledge | C2 |
| GOV-P-005 | Documentation is part of the product | C2 |
| GOV-P-006 | Knowledge ownership and lifecycle must be explicit | C2 |

---

# Architecture Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| ARC-P-001 | Generic Kernel Principle | C3 |
| ARC-P-002 | Kernel Bootstrap Principle | C3 |
| ARC-P-003 | Runtime and AI responsibilities remain separated | C3 |
| ARC-P-004 | Technology-specific concepts never belong in the Kernel | C3 |
| ARC-P-005 | Contracts before implementations | C2 |
| ARC-P-006 | Earned Abstractions | C2 |
| ARC-P-007 | Modular Monolith First | C2 |
| ARC-P-008 | Architecture evolves through incremental validated steps | C2 |
| ARC-P-009 | Deployment boundaries do not define architecture boundaries | C2 |
| ARC-P-010 | The Kernel and the KernelRuntime remain separated | C2 |
| ARC-P-011 | Capabilities define what AIStack can do; services provide them | C2 |
| ARC-P-012 | Providers observe and collect; they never decide or modify | C3 |
| ARC-P-013 | Evaluation consumes canonical knowledge models, never raw technical output | C2 |
| ARC-P-014 | Location abstracts physical storage | C2 |

---

# Standards Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| STD-P-001 | Documentation First | C2 |
| STD-P-002 | Specification before implementation | C2 |
| STD-P-003 | Official terminology must be preserved | C2 |
| STD-P-004 | One validated concept, one commit | C2 |
| STD-P-005 | Naming conventions are governed | C2 |

---

# Engineering Principles

| ID | Principle | Criticality |
|----|-----------|-------------|
| ENG-P-001 | The engineer's role is understanding, not writing code | C2 |
| ENG-P-002 | Industrial quality is achieved before implementation | C2 |
| ENG-P-003 | Generated artifacts are disposable | C2 |
| ENG-P-004 | Improve generators instead of generated artifacts | C2 |
| ENG-P-005 | Validate every architectural step independently | C2 |
| ENG-P-006 | Prefer simple modular maintainable solutions | C1 |

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
| OPS-P-001 | Deployment is Architecture | C2 |
| OPS-P-002 | Packaging is an architectural concern | C2 |
| OPS-P-003 | Rollback is mandatory for risky evolution | C1 |
| OPS-P-004 | Observe before acting | C2 |
