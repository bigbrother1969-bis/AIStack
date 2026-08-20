---
artifact:
  id: STD-0100
  title: Documentation Standard
  type: Documentation Standard
  semantic_type: Standard
  domain: Standards
  criticality: C2
  status: Proposed
  confidence: Declared
  version: 2.0
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-20

relations:
  references:
    - STD-0001
    - FDN-0003
    - FDN-0004
    - FDN-0005
    - FDN-MANIFESTO
---

# STD-0100 — Documentation Standard

## Purpose

This standard defines the canonical structure of every Knowledge Artifact produced within AIStack.

Its objective is to ensure consistency, traceability, readability and long-term maintainability.

---

## Provenance of version 2.0

Version 1.0 required eight metadata fields. The Context Bundle pipeline and the
Knowledge Integrity validator measured a different set — `domain`, `semantic_type`,
`criticality`, `confidence` — none of which this standard required, while ignoring
`version`, `created` and `updated`, which it did.

The validator was therefore reporting artifacts as deficient against a schema **no
standard governed**, and the Constitution was requiring a `confidence` whose scale had
never been written anywhere in the heritage.

Three schemas, no reconciliation. This version resolves it in favour of FDN-0003
Article 3 and Manifesto Article IV, which are C3 and conceptually upstream of any
standard: a standard that contradicts the Constitution yields.

**This is a breaking revision.** Documents compliant with 1.0 are not compliant with
2.0. The version is 2.0 rather than 1.1 for that reason.

Consequence to be carried out separately: the validator shall also observe `version`,
`created` and `updated`, which it does not today.

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

Every Knowledge Artifact shall begin with a governance metadata block, expressed as
YAML frontmatter under a single `artifact:` mapping.

Twelve fields are mandatory, grouped by what they answer.

## Identity — what this artifact is

| Field | Rule |
|---|---|
| `id` | Canonical identifier, per STD-0102. Stable across title changes. |
| `title` | Human-readable name. |
| `type` | Free descriptive label the artifact gives itself — *Foundation Document*, *Component README*, *Documentation Standard*. Not constrained. |
| `version` | Semantic. A breaking change to the artifact's meaning increments the major. |

## Classification — how this artifact is qualified

| Field | Vocabulary |
|---|---|
| `domain` | `Foundation` · `Architecture` · `Governance` · `Standards` · `Engineering` · `Knowledge Assets` |
| `semantic_type` | `Principle` · `Rule` · `Policy` · `ADR` · `Standard` · `Specification` · `Knowledge Artifact` |
| `criticality` | `C3` core and invariant · `C2` governed · `C1` operational and adaptable |

`type` and `semantic_type` are **two distinct fields and both are mandatory**. `type`
preserves the wording the artifact chose for itself; `semantic_type` places it in a
closed vocabulary the pipeline can reason over. Collapsing them would either destroy
the first or open the second, and an open vocabulary is not a vocabulary.

Both vocabularies are contractualised in `src/aistack/contracts/classification.py`.
The enumeration and this table are two projections of one decision: they shall not
drift apart.

## Governance — who answers for this artifact

| Field | Vocabulary |
|---|---|
| `owner` | The role or person accountable for the artifact. |
| `status` | `Draft` · `Proposed` · `Accepted` · `Published` |
| `confidence` | `Verified` · `Reviewed` · `Declared` |

### The confidence scale

FDN-0003 Article 3 and Manifesto Article IV both require a confidence level. Neither
defines one. This standard defines it, and defines it as **an act, not an
appreciation**:

- **`Verified`** — the artifact's claims have been checked against an execution, a
  measurement or a reproducible observation. What was verified, and when, is recorded
  in the artifact.
- **`Reviewed`** — a human other than the author has read the artifact and accepted
  its content.
- **`Declared`** — the artifact states what its author believes to be true. Nothing has
  been checked. This is the honest default for a new artifact.

A confidence level shall never be raised because the content feels solid. It is raised
by performing the act that the next level names. `High` / `Medium` / `Low` scales are
deliberately rejected: they make confidence an opinion about knowledge, and this
project's own position is that derived knowledge is not an opinion.

## Lifecycle — when

| Field | Rule |
|---|---|
| `created` | ISO date of first existence as a governed artifact. |
| `updated` | ISO date of the last substantive change. |

## Undeclared values

An absent field is reported as `unknown` and is **a governed state, not an error**
(FDN-0003 Article 12). It shall never be filled with a plausible default, by a human
in a hurry or by a machine.

Qualification is the human contribution (Article 4). No tool shall infer `domain`,
`semantic_type`, `criticality` or `confidence` from a path, a filename or a content
heuristic. A tool may apply a rule the human has declared; it may not author the rule.

## Optional metadata

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

- the twelve mandatory metadata fields are present and declared;
- `domain`, `semantic_type` and `criticality` hold a value from their vocabulary;
- mandatory sections exist;
- identifiers follow the naming convention;
- cross references use canonical identifiers.

A document declaring `unknown` on a mandatory field is **not compliant**, and is also
**not defective**: it is an artifact awaiting qualification. The distinction matters —
the first state is a measurement, the second would be a judgement.

---

# Related Artifacts

- STD-0001 — Standards
- FDN-0003 — Constitution (Article 3, Governance; Article 4, Qualification; Article 12, Uncertainty)
- FDN-0004 — Governed Heritage
- FDN-0005 — Project Operating Model
- FDN-MANIFESTO — The Sustainable Heritage Manifesto (Article IV)
