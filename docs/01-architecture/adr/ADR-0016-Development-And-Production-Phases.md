---
artifact:
  id: ADR-0016
  title: Development and Production Phases
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-10-04
  updated: 2026-10-04

relations:
  references:
    - ADR-0009
    - ADR-0011
    - ADR-0015
---

# ADR-0016 — Development and Production Phases

## Status

Accepted, 2026-10-04, by the owner, the day it was proposed — under the
rule this record itself sets for the development phase (§ 3).

## Context

*Measured on 2026-10-04, at commit `d350780` (1.7.0 published).*

Three rules of this heritage were written for an AIStack used by
several people over time, and bind today a heritage with one person
setting it up:

- **A second person validates an Explication** (`ADR-0015` § 3). With
  one administrator, everything the owner writes stays `Declared` for
  good — what the owner called, on 2026-10-04, a rule for "prod", not
  for "la phase de dev/mise au point actuelle".
- **Nothing written is ever removed** (`ADR-0011` § 7, R6). The first
  real trials of tranche 4 left three identical versions of a test text
  ("Test de développement") on `wordpress`, kept for good.
- **An act binding the heritage is proposed one day and accepted the
  next** — adopted 2026-08-21 (`ADR-0009` § Status) to stop a decision
  being fixed minutes after an agent framed it. On 2026-10-03 the owner
  accepted `ADR-0013` and `ADR-0014` the evening they were proposed, by
  explicit decision, and the records had to say they broke the rule.

## Decision

Decided by the owner, 2026-10-04.

### 1. AIStack declares its phase

`instance_config.yml` gains `phase`: `development` while the owner sets
AIStack up and refines it, `production` once it is used for real. **A
config that says nothing is in production**: the strict rules are the
default, and leaving development is one line.

### 2. Explications in the development phase

- An administrator's text is **validated as written**: the version is
  recorded `Validated`, its author as validator, marked
  `validated_in: development`; and an author may validate their own
  text. In production, `ADR-0015` § 3 applies unchanged.
- Every person's text still waiting (`Declared`, `Proposed`) is
  validated by `python -m aistack.cli.explications_admin
  validate-declared` — imported versions are left to be read one by one.
- A subject's whole history can be **purged** —
  `python -m aistack.cli.explications_admin purge <subject>` — for test
  entries; the graph forgets it at its next rebuild. The one exception
  to "nothing is ever deleted", run from the host, never from a page.

Both commands refuse in production.

### 3. Decision records in the development phase

While the phase is `development`, an ADR is **accepted the day it is
proposed** when the owner accepts it; the 2026-08-21 rule applies again
in production.

## Implementation state

| Step | State |
|---|---|
| § 1 — `phase` in `InstanceConfig` and `instance_config.yml` (`development`) | done — 2026-10-04 |
| § 2 — write validated as written, own validation, `explications_admin` | done — 2026-10-04 |
| § 3 — ADR acceptance the same day | done — 2026-10-04 (this record, `ADR-0015`) |

## Consequences

- `validated_in: development` keeps visible, version by version, what
  was validated under the lighter rules.
- Moving to production is a reviewed act: set `phase: production`, then
  the strict rules hold for everything written after.

## Open Points

- What else changes at the move to production is not decided.
