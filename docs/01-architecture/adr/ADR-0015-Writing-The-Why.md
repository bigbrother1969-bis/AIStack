---
artifact:
  id: ADR-0015
  title: Writing, Validating and Discarding the Why
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Accepted
  owner: Architecture
  created: 2026-10-03
  updated: 2026-10-04

relations:
  references:
    - ADR-0011
    - ADR-0012
    - ADR-0014
    - STD-0100
    - ADR-0016
---

# ADR-0015 — Writing, Validating and Discarding the Why

## Status

Accepted, 2026-10-04, by the owner.

Proposed 2026-10-03: the decisions below were taken by the owner that
day, at the start of 1.7's fourth tranche, verified for real the same
evening and published in 1.7.0. In the development phase, `ADR-0016`
§ 2 lightens § 3 and § 4 below: a text is validated as written, its
author may validate it, and a subject's history can be purged.

## Context

*Measured on 2026-10-03, at commit `6ae7679`.*

An Explication — the "why" of a subject — is a `KnowledgeArtifact`
(`ADR-0011` § 7) kept per subject under
`reports/generated/explications/`, every version in its history. Four
importers write them, all at confidence `Proposed` with
`explication_status: Proposed`: commit messages, `pra_tests.yml`'s
comments, the AI Runtime's `explain` answers, the `claude/` notes
(`ADR-0011` § 8). `timemachine_rebuild` projects each version into the
graph: its existence, when, what it explains, its confidence, its
status, and who it is attributed to.

The Time Machine's `/timemachine/explication` page shows every version,
read-only; its own comments said correcting one "stays a CLI act" — and
no CLI does it. `ADR-0011` § 7 already decided the model: a correction
is a new version linked to its predecessor by `prov:wasRevisionOf`; a
validation makes a human a second, confirming author (a second
`prov:wasAttributedTo`); a discarded Explication is kept, never deleted
(`Discarded`). Neither the link nor the second author is written by
anything yet.

Tranche 3 (`ADR-0014`) gives every request a person and a profile.

## Decision

### 1. Who

Decided by the owner, 2026-10-03: **only an administrator** writes,
validates or discards an Explication. A user reads them, as every page.
The three are actions under `ADR-0014` § 2 and § 3 (`ADMIN_ACTION`,
the session's CSRF token).

### 2. Writing — a new version, `Declared`

Writing is one act, whether the subject had no Explication yet or its
current one is corrected (the form starts from the current text):

- a new version: confidence **`Declared`** (decided by the owner — a
  named human states it; `STD-0100`), `explication_status: Proposed` —
  it waits for a second person's validation;
- `source` is the person — `person:<Pocket ID subject>`, or
  `person:local-admin` for the fallback administrator — and
  `metadata.author_name` the name shown;
- `metadata.revision_of` names the version it revises, when there was
  one.

The text is required, at most 20 000 characters, kept exactly as typed.
Recording the current version's text again is refused — it says nothing
new (measured on GIGABYTE, 2026-10-03: two identical versions in a row);
after a discard, the same text may be written again, as a new claim.

### 3. Validating — a second author

- Only the current version, when it is neither `Validated` nor
  `Discarded`.
- **Never by its own author**: validating is a second person
  confirming; a person who wrote the text has nothing to confirm. The
  page does not offer its author the button; it says why instead. An
  imported version (a commit, a model, a note) has no human author, so
  any administrator may validate it.
- A new version with the same text, the same author and confidence,
  `explication_status: Validated`, `metadata.validated_by` (and its
  name), `metadata.revision_of` the version validated.

### 4. Discarding — with a reason

- Only the current version, when it is not already `Discarded`.
- **A reason is required** (decided by the owner): one sentence, at
  most 1 000 characters, kept as `metadata.discard_reason` with
  `metadata.discarded_by`.
- A new version with the same text and author,
  `explication_status: Discarded`, `metadata.revision_of`. Nothing is
  deleted; writing again later starts a new `Proposed` version.

### 5. One page, the graph at the next rebuild

Decided by the owner: the three actions are forms of
`/timemachine/explication` (LAN only, `ADR-0012`), shown to an
administrator only. The page reads the store, so an action is visible
at once; **the graph sees it at the next `timemachine_rebuild`**, which
projects two new facts:

- `prov:wasRevisionOf`, from a version to the one its
  `metadata.revision_of` names;
- a second `prov:wasAttributedTo`, to the validating person's agent.

Who discarded and why stay in the store, not in the graph — the graph
already holds no Explication's text.

The Time Machine stays **read-only against the graph** (`ADR-0011`
§ 13): it never opens it for writing and never triggers a rebuild. What
it writes is the Explications store, one of the graph's sources —
`ADR-0011` § 13's "never a writer" is narrowed to the graph, for this
one store.

### 5 bis. The list of every subject with a why

Asked by the owner, 2026-10-03, after the first real trials — the 80
imported subjects are repository topics (`pra`, `timemachine`,
`1.0.0`…), none in the network tree, so no page led to them:
`/timemachine/explications`, a fourth view beside Streams, Tree and
Ribbon, lists every subject that has an Explication with its current
version's status, confidence, author, validator, date and number of
versions, filtered by status and by a word of the subject; each line
opens that subject's page. It reads the Explications store, so it
answers before any graph is built. Signed in to read, like every
Time Machine page.

### 6. Two administrators acting at once

Every form carries the number of versions it was drawn from; an action
on a subject whose history has changed since answers `409`, saying the
page must be reloaded — never a second version on top of one its
author has not seen.

## Implementation state

**As of 2026-10-04** — published in 1.7.0, verified for real on
GIGABYTE on 2026-10-03.

| Step | State |
|---|---|
| § 2 — writing, `Declared`, the same text refused | done — 2026-10-03 |
| § 3 — validating, never one's own text (production) | done — 2026-10-03 |
| § 4 — discarding with a reason | done — 2026-10-03 |
| § 5 — the forms, the graph at the next rebuild | done — 2026-10-03 |
| § 5 bis — the Explications list | done — 2026-10-03 |
| § 6 — 409 on an out-of-date page | done — 2026-10-03 |

## Consequences

- An administrator can bring the why of any subject up to `Declared`,
  then `Validated` by someone else; until a second administrator
  exists, what the owner writes stays `Declared` and `Proposed` — the
  one-person validation `ADR-0011` § 7 rules out.
- An importer run after a human act adds its own `Proposed` version on
  top, as today; it never rewrites one.
- The page's comments and catalog no longer say correcting is a CLI
  act.

## Open Points

- The fallback administrator (`person:local-admin`) and the owner's
  Pocket ID account are two sources for one person: one can validate
  what the other wrote. Not prevented — recorded.
