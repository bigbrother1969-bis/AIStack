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
  version: 1.4
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-21

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

Canonical Knowledge Artifacts shall follow the pattern:

```text
<ID>-<Title>.md
```

Examples:

```text
FDN-0003-Constitution.md

STD-0100-Documentation-Standard.md

ADR-0001-Python-Packaging-v1.md

ARCH-0002-Kernel-Architecture.md
```

A file name carries the identifier and the title, and nothing
else. Criticality in particular does not belong here: it is a
declared qualification that may change, and encoding it in the
name creates a second source for one fact and a rename the day
it moves. Five architecture documents carried a `-C1` or `-C2`
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

## Three digits or four

The same prefixes name two different things, and only the width
of the number tells them apart:

| Form | Names | Lives in |
|---|---|---|
| `FDN-004`, `STD-004`, `GOV-001` — **three digits** | a **principle** | a row of PRINCIPLES-REGISTRY |
| `FDN-0004`, `STD-0100`, `GOV-0001` — **four digits** | an **artifact** | a file of its own |

This convention was already in force across the heritage on
2026-08-21 — `STD-004` is *one validated concept, one commit*,
`STD-0100` is this family of standards — but it had never been
written down, so nothing prevented a reader from taking one for
the other.

**A single digit is a thin signal, and this standard does not
pretend otherwise.** Architecture escaped it on 2026-08-21 by
giving documents their own prefix, `ARCH-`. `FDN-`, `STD-` and
`GOV-` still rely on the digit width alone, and the same remedy
is available to them. Recording the weakness is the minimum; it
is not the fix.

Identifiers never change.

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
