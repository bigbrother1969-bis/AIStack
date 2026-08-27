---
artifact:
  id: STD-0100
  title: Documentation Standard
  type: Documentation Standard
  semantic_type: Standard
  domain: Standards
  criticality: C2
  status: Published
  confidence: Reviewed
  version: 2.5
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-27

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

Version 2.0 was drafted by an AI assistant, read and accepted by the owner, and
engraved — *Gravé* — on 2026-08-20. It therefore declares `confidence: Reviewed`, which
is the level its own scale defines for that act. It is not `Verified`: no execution has
yet checked that the heritage conforms to this schema.

Consequence carried out separately, and **discharged on 2026-08-21** by `085fe3b`:
the validator observes `version`, `created` and `updated`. Until 2026-08-22 this
paragraph still read *"which it does not today"* — a statement about the code that
had stopped being true a day after it was written.

That is recorded rather than quietly rewritten, because the defect is not the
deferral. A deferral honoured within a day is the standard working. The defect is
that nothing distinguished a live deferral from a discharged one, in a document or
anywhere else — which is why a debt register was decided on 2026-08-22.

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
| `domain` | `Foundation` · `Architecture` · `Governance` · `Standards` · `Engineering` · `Operations` · `Knowledge Assets` |
| `semantic_type` | `Principle` · `Rule` · `Policy` · `ADR` · `Standard` · `Specification` · `Knowledge Artifact` |
| `criticality` | `C3` core and invariant · `C2` governed · `C1` operational and adaptable |

`type` and `semantic_type` are **two distinct fields and both are mandatory**. `type`
preserves the wording the artifact chose for itself; `semantic_type` places it in a
closed vocabulary the pipeline can reason over. Collapsing them would either destroy
the first or open the second, and an open vocabulary is not a vocabulary.

Both vocabularies are contractualised in `src/aistack/contracts/classification.py`.
The enumeration and this table are two projections of one decision: they shall not
drift apart.

`Operations` was added to both on 2026-08-22. The heritage had carried Operations
principles since July — `OPS-P-001` to `OPS-P-004` — while the domain existed in
neither the table nor the enumeration. An artifact declaring `domain: Operations`
would have been normalized to `unknown`: the domain was missing from the
implementation, not from the knowledge.

### A declared `type` determines its `domain`

Every distinct `type` in the heritage maps to exactly one `domain`. Measured on
2026-08-22 across 63 artifacts and 16 distinct types, re-measured on 2026-08-23
across 65 artifacts and 19 types: no exception either time. Two artifacts
declaring the same `type` and different `domain` values would give the heritage two
answers to one question, and that is not permitted.

Since 2026-08-23 the rule is derived rather than applied: the
`classification-coherence` check reads it off every projection, and
`test_no_declared_type_maps_to_two_domains` runs it over this repository's own
heritage at every suite. For the day between the two dates the rule was written
into this C2 standard and verified by nothing — GOV-0002/OS-004, now resolved.

`type` does **not** determine `semantic_type`, and does **not** determine
`criticality`. The same measurement found one counterexample to each, and both are
correct:

- `FDN-0011` is a `Foundation Document` whose `semantic_type` is `Principle`, where
  the eight others are `Knowledge Artifact`. The type says where an artifact sits;
  the semantic type says what it is.
- `ARCH-0009` is an `Architecture Document` at `C1` where the thirteen others are
  `C2`. Criticality is a judgement about importance, not a consequence of document
  kind — the same reading that kept the repository README at `C2` on 2026-08-21,
  since reading priority is not criticality.

Those two are named here so that a later reader does not complete the rule by
extending it to three axes, and break two artifacts doing so.

From 2026-08-22 to 2026-08-23 this paragraph read *"This rule is stated and not
yet enforced. No integrity check verifies it; it holds because it has been applied
by hand."* It is left visible here rather than deleted: the sentence was exact
when written, and the register entry it produced — OS-004 — is what got the check
written. A standard that erased its own deferrals would show only rules that had
always been enforced.

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

## An assertion about the code carries its date

A sentence stating what the code does, does not do, or does not do *yet* shall
name the date it was measured and, where one exists, the commit that measured
it. Without them, a statement about a moving system reads as a permanent
property of it.

> ✗ the validator does not observe `version`, `created` and `updated` today
> ✓ as of 2026-08-20, the validator does not observe `version`, `created` and
>   `updated` (discharged 2026-08-21 by `085fe3b`)

The words that require this treatment are the ones that hide a date inside
themselves: *today*, *currently*, *not yet*, *for now*. Each means "at the time
of writing", and none says when that was.

**Two words were removed from that list on 2026-08-27, by measuring it.** It
had read *today, currently, still, not yet, remains, for now* since 2026-08-22,
written from intuition. Across the 66 artifacts, `remains` accounted for 50 of
113 occurrences and `still` for 27, and reading them showed why: they
overwhelmingly introduce statements that hide no date at all — *the repository
remains the authoritative source of governed knowledge*, *refactoring remains
safe*. Keeping them would have published over a hundred lines, and a report
nobody can read is not a report.

**Since 2026-08-27 the rule is observed rather than enforced.** The
`undated-assertions` check lists every line carrying one of the four markers
without a date or a commit, at every projection, as an `OBSERVATION` — 19 lines
when it was written. It never says `clean: False`, because whether a sentence
carrying a marker has gone stale is not derivable and this standard does not
pretend otherwise. What is derivable is where to look.

A quotation is not an assertion, and the check knows it: the marker list two
paragraphs above, and the ✗ example above that, are quotations of the rule and
are not reported. That is also why no artifact is excluded by name — excluding
a file for being noisy would be a check adapting to the data rather than to the
rule.

GOV-0002/OS-017 recorded six occurrences in three C2 artifacts over two days,
two of them inside the documents that state this rule, and the owner decided on
2026-08-23 that the check was worth its false positives. Roughly a third of
what it lists are real; the rest are rhetoric — *Ollama today and another engine
tomorrow* — or definitions. That figure is stated so that a reader knows what
kind of instrument this is.

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
