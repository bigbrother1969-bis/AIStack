---
artifact:
  id: ADR-0027
  title: GHE Reintegration
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-11-15
  updated: 2026-11-15

relations:
  references:
    - FDN-0001
    - FDN-0003
    - FDN-0004
    - FDN-0012
    - GOV-0002
    - STD-0300
    - ADR-0004
    - ADR-0016
    - ADR-0019
---

# ADR-0027 — GHE Reintegration

## Status

Accepted, 2026-11-15, by the owner, the day of the proposal
(`ADR-0016` § 3). Each decision below was taken by the owner that day, one
by one, as the measures that motivate it were produced.

## Context

From 1.2 to 2.0 the roadmaps were driven by features. On 2026-10-10 the
release candidate of 2.0.0 removed from `main` what nothing ran
(`19e73a6`, 382 files) and kept only the documents that describe the
product (`94f7c15`, 122 files). The heritage is whole at the tag
`archive/heritage-2.0.0-rc1`.

Two things left with it that the product still depended on:

- **the principles.** The code cites them by identifier — `ARC-P-006` 46
  times, `GOV-P-001` 23 times — and the registry that defines them was no
  longer beside it. Nor were the Constitution, the Glossary and the
  Manifesto. A session working in `main` could not read what it was asked
  to respect;
- **the validator.** `aistack.cli.knowledge_integrity` and its checks were
  the only thing that verified the heritage. Nothing replaced them.

Measured on 2026-11-15 by `scripts/ghe_audit.py`, written that day:

| Principles | Departure | Count |
|---|---|---|
| `ARC-P-001`, `ARC-P-004` | The Kernel names something outside itself | 10 imports |
| `ARC-P-002` | An entry point never builds the Kernel | 22 of 25 |
| `ARC-P-002` | The one registered Task is never executed | 1 |
| `GOV-P-002`, `ARC-P-012` | The disk is written outside a transaction | 35 files |
| `FDN-P-005` | A document is cited and is not in the tree | 22, once the first fifteen had returned |

The Kernel Runtime itself is at the tag: `kernel/runtime` no longer
exists, and the Task `docker.discover` is registered and reached by
nothing.

The Manifesto forbids the obvious answer. *Preserve working heritage.
Migrate incrementally. Do not rewrite functioning code because a cleaner
architecture exists.* 2.0.0 is in production and its suite is green.

## Decision

### 1. The core of the principles returns to `main`; the rest stays at the tag

Option B of three. Not everything (it would undo the decision of
2026-10-10 and bring back some 58 000 lines, much of it unexecuted), and
not a separate repository (two sources, and the principles still out of
sight where the work is done).

Returned on 2026-11-15: the Manifesto (amended, 1.1), `FDN-0001` to
`FDN-0004`, `FDN-0007` to `FDN-0012`, `ENG-TEST-0001`, `ENG-TEST-0002`,
`STD-0100`, `STD-0102`, `STD-0300` (requalified against 2.0.0),
`GOV-0002` (its rules, and a new history), `OPS-0001`, `OPS-0003` and
`ARCH-0009`.

### 2. Nothing returns without a use

A document returns when it is read or verified. A module returns in the
lot that executes it. Nothing is restored in bulk from the tag.

### 3. What stays at the tag is declared in one place

`FDN-0001` § *Kept at the tag* lists the documents that do not return. A
citation of one of them leads there. No citation is rewritten.

### 4. The departures are measured, and the list only gets shorter

`scripts/ghe_audit.py` reads `src/aistack` and the documents, and
reports every departure it can measure.
`tests/reference/ghe_audit_baseline.json` records them. The governed
suite fails on a departure that is not in the baseline, and on a baseline
entry that no longer exists.

It is a script and a test, not the nineteen checks of the validator: it
verifies what is cited, registered and imported, and nothing about the
content of a document.

**The baseline was extended twice on 2026-11-15**, by one entry each
time: a returning document (`FDN-0002`, then `STD-0300`) cited a
document that had not returned (`ARCH-0010`, then `STD-0200`). Both are
recorded in their commits. A returning document brings its citations
with it; that is the only case in which an entry is added.

### 5. The code is brought back within the principles in lots

Each lot is a series of atomic, reversible commits, validated on the
production of 2.0.0 — the suite green, the Cockpit unchanged, the
generated artifacts compared before and after. The owner decides at the
end of each lot.

| Lot | Subject | Closes |
|---|---|---|
| 3 | No technology in the Kernel | `GOV-0002/OS-085` |
| 4 | Capabilities registered at bootstrap; services exposed | part of `OS-086` |
| 5 | The chains run through the Kernel, one at a time: health, architecture, console, Time Machine | `OS-086`, `OS-089` |
| 6 | Modifications of knowledge go through a transaction | `OS-087` |
| 7 | The declarations edited by hand on the host become governed knowledge | — |
| 8 | Self-onboarding: host executors, Context Bundle, boot report | VS-2 of `STD-0300` |

The architecture documents of the Kernel and of its concepts
(`docs/01-architecture/kernel/` and `docs/01-architecture/concepts/` at
the tag) return revised with lots 3 to 5, and `ADR-0005` to `ADR-0007`
and `ARCH-0013` with lot 8: they describe code
that is at the tag, and return when the code they describe does.

### 6. No abstraction without a present case

`ARC-P-006`. A lot moves what exists behind the Kernel. It builds nothing
the product does not already do.

## The refactoring plan of August 2026

`AIStack-Refactoring-Plan` (draft v1, 2026-08-13) was the first plan to
bring the bootstrap within the principles. It was never a governed
document and none of its boxes was ticked. Read against the tag and
against `main`:

| Phase | Subject | State |
|---|---|---|
| 1 | Clean the heritage: one definition per concept, no transport artifact left | done at the tag, 2026-08-20 and 2026-08-21 (`fa0fc00`, `6569f91`, `748b1c6`) |
| 2 | One responsibility per concept: repository, Context Bundle, README | done at the tag: *the Context Bundle is the Knowledge Package of AIStack*, 2026-08-29 |
| 3 | The README as bootstrap specification | not in `main`: the README of 2.0.0 presents the product |
| 4 | A Knowledge Acquisition Protocol as a Foundation concept | never written: the term appears in no governed document, at the tag or in `main` |
| 5 | One Boot Report | verified once, `STD-0300` 2.1, 2026-08-14; not verifiable in `main` |
| 6 | Knowledge integrity | built — nineteen checks — and removed on 2026-10-10 |
| 7 | The Context Engine implements the protocol | never built |
| 8 | Onboarding tested with several models | `STD-0300` 2.4, never verified |

Phases 3 to 8 are lot 8 of this decision. Phase 4 is decided there, not
here: whether the protocol becomes a Foundation concept is the owner's.

## Consequences

- A session working in `main` reads the principles in `main`.
- Five weeks of the project have no open-state register. `GOV-0002` 2.0
  says so and does not reconstruct them.
- `STD-0300` no longer reads 17 of 22. For 2.0.0: 2 verified, 9 satisfied
  before 2.0.0 and not re-run, 6 not verifiable in `main`, 5 not
  verified.
- Two architecture guards pass on nothing until lot 5 (`OS-089`), kept
  by decision.
- The audit measures imports and citations. It does not tell a generated
  artifact from a modification of knowledge, and it does not verify that
  a chain which builds the Kernel runs through it.

## Open points

- How the nine criteria of `STD-0300` are re-run on 2.0.0
  (`GOV-0002/OS-091`).
- Whether criterion 3.2 gets its explanation back (`OS-090`).
- `OPS-0009` and `QUAL-0001` are cited and were never documents under
  `docs/` (`OS-092`).
- The order of the chains in lot 5 is a proposal; the first one decides
  the shape of the others.
