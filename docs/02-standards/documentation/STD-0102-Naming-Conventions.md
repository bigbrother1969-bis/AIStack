---
artifact:
  id: STD-0102
  title: Naming Conventions
  type: Documentation Standard
  semantic_type: Standard
  domain: Standards
  criticality: C2
  confidence: Declared
  status: Published
  version: 2.3
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-27

relations:
  references:
    - STD-0001
    - STD-0100
    - STD-0101
---

# STD-0102 — Naming Conventions

## Purpose

This standard defines the official naming conventions used throughout the AIStack Governed Heritage.

Consistent naming improves readability, discoverability, traceability and long-term maintainability.

---

# General Principles

Names shall be:

- explicit;
- stable;
- unambiguous;
- technology-independent whenever possible.

Names should describe responsibilities rather than implementations.

---

# Language

Canonical names shall be written in English.

Abbreviations should only be used when officially defined.

---

# The Name Of The Project

The project is written **AIStack**: capital A, capital I, capital
S, lowercase t-a-c-k. The Python distribution and the package are
written `aistack`, lowercase, as PEP 8 requires.

No other spelling is canonical. `AISTack` in particular is not,
and it exists: the Codeberg mirror is named
`bigbrother1969/AISTack` and the SPOT host holds its clone at
`/srv/aistack/AISTack`, while Gitea and GitHub both use
`AIStack`. A single run of `scripts/sync_mirrors.sh` prints both
spellings.

Neither of those two is inside this repository, and neither can
be corrected from it. They are recorded here so that the
divergence is a known deployment fact rather than a recurring
question, and so that nobody propagates the wrong one into
governed knowledge on the grounds that they saw it somewhere.

Two occurrences of `AISTack` inside the repository are correct
and shall not be normalized:

- `tests/unit/scripts/test_repository_url.py` reproduces the real
  Codeberg and tunnel URLs. A fixture that corrected reality
  would stop testing it.
- `reports/qualification/2026/07/` records paths observed on the
  SPOT host in July. A recorded observation is not editable.

---

# File Names

**A file name is not governed.** The rule that it must follow
`<ID>-<Title>.md` was retired on 2026-08-27, and what replaced it
is nothing: an artifact's identity is `id`, declared in its
frontmatter, and where its text happens to sit is a convenience
for whoever browses the tree.

## Why it was retired

The rule was measured against the heritage it governs on
2026-08-23, before a check was written to enforce it. **25 of the
65 artifacts did not follow it**, and they were not 25 mistakes.
They were families, and at least three of them are deliberate:

- **components.** `CMP-0001` through `CMP-0012` each hold
  `README.md`, `architecture.md` and `specification.md` inside
  their own directory. That is a coherent convention — and it
  produces four files named `architecture.md`, so a file name no
  longer identifies an artifact even in principle;
- **section READMEs.** `FDN-0001-README.md`, `STD-0001-README.md`,
  and the repository's own `README.md`, whose declared title is
  *AIStack Main README*;
- **the Manifesto**, `The-Sustainable-Heritage-Manifesto.md`,
  declaring `id: FDN-MANIFESTO` — a name chosen to be read, on the
  document that opens the heritage.

The rest are near-misses where the declared title is longer than
the file name: `ADR-0005-Context-Bundle-Engine.md` declares
*Context Bundle Engine Architecture*, and three others like it.

A rule that reports 38% of what it governs as non-conforming is
not describing that heritage. Enforcing it would have meant
renaming 25 files to satisfy a constraint that had stopped
carrying anything.

## What carries identity instead

Since 2026-08-23 the Context Bundle is keyed on the declared `id`
(GOV-0002/OS-021). Before that a bundle held 65 artifacts
identified by content hash, and `FDN-0003` appeared nowhere in the
model — which is the state in which a file name was the only
human-readable handle an artifact had. That is no longer true, and
the rule outlived the reason for it.

`reference-integrity` resolves every declared reference against
`id`. `principle-identifiers` reads the rows of FDN-0012. Neither
looks at a path.

## What is still true

**Identifiers never change**, and that rule is untouched — it
governs `id`, not the file holding it. A file may be renamed
freely; renaming what it declares breaks every reference ever
written.

Two file names were corrected before the rule was retired, and
both were right to correct: `FDN-PRINCIPLES` → `FDN-0012`
(GOV-0002/OS-006), which was an *identifier* change and cost five
citations, and `ADR-0003-Selection-Engine.md` →
`ADR-0003-Selection-Engine-Strategy-Delegation.md`
(GOV-0002/OS-007), a rename that touched nothing. A file whose
name contradicts its declared title is still worth fixing when
someone notices. What is retired is the obligation, not the
courtesy.

A file name carries whatever helps a reader find it.
**Criticality does not belong there**, and that has not changed:
it is a declared qualification that may move, and encoding it in
a name creates a second source for one fact and a rename the day
it changes. Five architecture documents carried a `-C1` or `-C2`
suffix until 2026-08-21.

---

# Directory Names

Directories describe domains rather than artifacts.

Examples:

```text
00-foundation/

01-architecture/

02-standards/

03-governance/

04-development/

templates/

documentation/

specifications/
```

Directory names shall remain stable.

---

# Knowledge Artifact Identifiers

Every canonical Knowledge Artifact has a unique identifier.

Examples:

```text
FDN-0005

STD-0100

CMP-0001

ADR-0001

ARCH-0002
```

| Prefix | Domain |
|---|---|
| `FDN-` | Foundation |
| `STD-` | Standards |
| `ARCH-` | Architecture — descriptions of the system as it is |
| `ADR-` | Architecture Decision Records — a decision, with its context and consequences |
| `CMP-` | Components |
| `GOV-` | Governance |
| `OPS-` | Operations — knowledge about running this deployment |

`OPS-` was added on 2026-08-22, for `OPS-0001`, the catalogue of
container log signatures. The heritage had carried Operations
*principles* since July while having no prefix for an Operations
*document* and no `Operations` value in the domain vocabulary; a
document declaring that domain would have been normalized to
`unknown`. Both were opened the same day.

The family is `OPS-0001` for documents and `OPS-P-001` for
principles, as for `FDN-`, `STD-` and `GOV-`. The four Operations
principles carried the old three-digit form until 2026-08-22,
having been missed by the renumbering of the day before — which
is how the gap was found.

`ARCH-` and `ADR-` are both architecture and are deliberately
distinct: an ADR records *a decision taken at a point in time*
and does not change once accepted, while an ARCH describes *the
architecture as it stands* and evolves with it.

`ARCH-` carries four letters where every other prefix carries
three. That is deliberate. The registry uses `ARC-` for
architecture *principles*, and a three-letter architecture
prefix for documents would have left `ARC-001` and `ARC-0001`
distinguishable by one digit alone. `ARD-` was rejected for a
worse reason: `ADR-0004` and `ARD-0004` differ only by the order
of two letters.

`GOV-` follows the same pattern for governance documents.

## Principles and artifacts

A principle and an artifact are different governed objects, and
their identifiers say so:

| Form | Names | Lives in |
|---|---|---|
| `FDN-P-004`, `STD-P-004`, `GOV-P-001` | a **principle** | a row of FDN-0012 |
| `FDN-0004`, `STD-0100`, `GOV-0001` | an **artifact** | a file of its own |

The `P` is the whole point. Until 2026-08-21 principles used
three digits and artifacts four, and nothing else distinguished
them. Fifteen pairs then differed by one leading zero while
naming unrelated things — `FDN-005` is *every knowledge item has
a Single Point Of Truth*, `FDN-0005` is the Project Operating
Model; `STD-004` is *one validated concept, one commit*,
`STD-0002` is Test Artifact Isolation.

An earlier version of this section recorded that weakness,
observed that architecture had escaped it by giving documents
the `ARCH-` prefix, and said plainly that recording it was not
fixing it. The fix came when the risk stopped being theoretical:
`FDN-0011` was registered as an artifact on 2026-08-21, one zero
away from the principle `FDN-011`, which already existed.

Architecture keeps `ARC-P-NNN` for principles and `ARCH-NNNN`
for documents. The two mechanisms differ because they were
decided a day apart; both make the families unmistakable, which
is what the standard requires.

Since 2026-08-23 the form is derived rather than applied. The
`principle-identifiers` check reads every row of FDN-0012 at each
projection and reports any that does not carry
`<DOMAIN>-P-NNN` — writing `FDN-006` into the registry would no
longer pass — and it reports separately any principle the
heritage cites that no row declares. The closed set of domain
prefixes is contractualised in
`src/aistack/contracts/classification.py` beside the domain
vocabulary, for the same reason: one decision, and the
projections of it must not drift apart.

`Knowledge Assets` has no prefix. No principle has been
registered in that domain, so none has been decided, and the
check reports an identifier using one as malformed rather than
inventing the answer.

**The old three-digit form in prose is deliberately not
checked.** Fourteen occurrences remain in the heritage, measured
2026-08-23, every one of them a quotation: this section and
FDN-0012 both recount the renumbering, and neither can do so
without naming what it retired. A check over prose cannot tell a
quotation from a live citation, and would report a heritage that
documents its history as one that failed to migrate. What is
checked instead is the registry itself and the citations that
resolve against it — GOV-0002/OS-005.

## Identifiers never change

An identifier is how the heritage refers to itself. Renaming one
silently breaks every reference ever written to it, including
those outside this repository.

The renumbering of 2026-08-21 is the one exception, decided by
the owner and recorded in FDN-0012 v2.0. Its scope is
worth stating precisely: **principles only**. No artifact
identifier changed and no governed file was renamed. The
exception was affordable because every principle identifier
lives in a single table plus its citations; the same operation
on artifact identifiers would have touched fifteen C3 files,
their names, their frontmatter and every cross-reference.

Titles may evolve.

---

# Component Names

Components shall be named according to their responsibility.

Examples:

- Context Bundle Generator
- Knowledge Block Registry
- Port Runtime Observer

Avoid implementation-specific names.

---

# Variables

Configuration keys should use:

```text
snake_case
```

Examples:

```text
artifact_type

generation_date

context_bundle
```

---

# Classes

Class names should use:

```text
PascalCase
```

Examples:

```text
GovernedArtifact

KnowledgeArtifact

ContextBundleGenerator
```

---

# Functions

Functions should describe actions.

Examples:

```text
generate_bundle()

load_artifacts()

validate_metadata()
```

---

# Commits

Commit messages shall begin with the Knowledge Artifact identifier.

Examples:

```text
FDN-0005: Introduce Project Operating Model

STD-0100: Introduce Documentation Standard

CMP-0001: Implement Context Bundle Generator
```

---

# Future Evolution

Additional naming conventions may be introduced for:

- APIs
- Python packages
- Docker services
- Configuration files
- Reports

Naming conventions shall remain backward compatible whenever possible.

---

# Related Artifacts

- STD-0001 — Standards
- STD-0100 — Documentation Standard
- STD-0101 — Writing Rules
