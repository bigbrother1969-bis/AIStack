---
artifact:
  id: FDN-0011
  title: Contract-Based Engineering
  type: Foundation Document
  semantic_type: Principle
  domain: Foundation
  criticality: C3
  confidence: Reviewed
  version: 1.1
  status: Published
  owner: Foundation
  created: 2026-07-24
  updated: 2026-08-21

relations:
  references:
    - FDN-0003
    - FDN-0004
    - STD-0300
    - PRINCIPLES-REGISTRY
---

# FDN-0011 — Contract-Based Engineering

## Provenance

These two principles lived in `engineering-principles-additions.md`, a
working file name, with no identifier, no metadata and no owner. Neither
is registered in PRINCIPLES-REGISTRY: verified on 2026-08-21, the terms
*contract debt*, *contract first* and *technical debt* appear nowhere in
it.

The content is unchanged. Only the heading levels were normalised and the
governance block added.

**Gravé — 2026-08-21.** This artifact is governed heritage. What is
engraved is an *adoption*: the wording is that of
`engineering-principles-additions.md`, unchanged, and what the governance
block added was ownership and identity, not content. The risk is therefore
not in the text but in what it commits AIStack to. `confidence: Reviewed`:
read and accepted by the owner.

It was engraved after one day of use rather than on the day it was written.
That day produced its first measurement — the `Registry` Protocol required
`contains` and `items`, which no implementation provided, and
`MutableRegistry` required a `freeze()` that existed nowhere. Principle 1
below is what makes that an orphan contract rather than an opinion about
code.

**Why this matters beyond bookkeeping.** STD-0300 § VS-4 asks AIStack to
derive technical debt from observations rather than from opinion. The
first principle below is what makes that possible: it defines technical
debt as a property of the contracts, countable from explicit
architectural observations. The acceptance criteria were governed while
the principle they rest on was not.

---

# Principle 1 — Technical Debt Is Contract Debt

## Statement

Technical debt is not primarily a property of the implementation.

It is primarily a property of the architectural contracts.

A governed architecture minimizes technical debt by ensuring that every concept is represented by a single, coherent, explicit and governed contract.

Implementations are expected to follow these contracts.

## Contract-Based Technical Debt

Technical debt is derived from violations of the contract architecture rather than from subjective code reviews.

Typical sources of technical debt include:

- Missing contracts
- Incorrect contracts
- Duplicated contracts
- Orphan contracts (no implementation)
- Orphan implementations (no governing contract)
- Contracts violating the Single Responsibility Principle
- Contracts describing obsolete or unused concepts

## Technical Debt Evaluation

Technical debt becomes measurable rather than subjective.

It can be evaluated from explicit architectural observations such as:

- Number of missing contracts
- Number of duplicated contracts
- Number of orphan contracts
- Number of orphan implementations
- Number of contract responsibility violations

The objective is not merely to reduce implementation complexity.

The objective is to maintain a coherent governed conceptual model.

## Engineering Consequence

In Governed Heritage Engineering, architecture quality is primarily determined by the quality of its contracts.

Well-designed contracts naturally lead to simple implementations.

Poor contracts inevitably generate technical debt, regardless of implementation quality.

Therefore, reducing technical debt consists first in improving the contract architecture rather than refactoring implementation details.


---

# Principle 2 — Contract First Engineering

---


The primary deliverable of software engineering is not code.

It is a coherent, governed set of architectural contracts.

Once contracts are stable, implementations become largely mechanical.

Engineering effort should therefore focus primarily on discovering concepts, assigning responsibilities and designing contracts before writing implementation code.

This approach minimizes avoidable technical debt and naturally produces maintainable software.
