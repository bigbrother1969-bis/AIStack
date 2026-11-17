---
artifact:
  id: FDN-0001
  title: Foundation README
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 1.4
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-11-17

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0004
    - FDN-0012
    - FDN-0013
---

# AIStack Foundation

## Purpose

The AIStack Foundation defines the fundamental principles, concepts and architectural vision of AIStack.

It is the highest level of the AIStack Governed Heritage.

The Foundation is intentionally technology-independent. It describes what AIStack is, why it exists and the principles that govern its evolution.

Implementation choices, programming languages, frameworks and tools are documented elsewhere.

---

## Scope

The Foundation contains the long-term knowledge that should remain stable regardless of future implementations.

It includes:

- The Constitution
- Core Principles
- The Sustainable Heritage Manifesto
- The Semantic Core
- The Governed Heritage model
- The official Glossary
- The AIStack Engineering Method

---

## Repository Governance

The AIStack Git repository is the Single Point of Truth (SPOT) for the Governed Heritage.

Conversations are workshops used to explore ideas.

Only validated Knowledge Artifacts committed to the repository become part of the official Governed Heritage.

---

## Working Workflow

Every Foundation contribution follows the same lifecycle.

*This is `FDN-0007`'s Governed Engineering Cycle at the scope of a Foundation
contribution — that cycle is the SPOT of the lifecycle, and this is one of its
two declared instances. Stated 2026-08-28; both had existed since 2026-07-06
with no sentence relating them.*

```text
Exploration
      ↓
Discussion
      ↓
Validation
      ↓
Knowledge Artifact
      ↓
Git Commit
      ↓
Governed Heritage
```

---

## Language

English is the official language of the AIStack Governed Heritage.

Discussions may happen in any language.

All Knowledge Artifacts are written in English.

---

## Guiding Philosophy

AIStack is not built by accumulating technologies.

AIStack is built by progressively discovering and governing the knowledge that explains Digital Ecosystems.

Technology serves the Heritage.

The Heritage serves understanding.

Understanding enables sustainable evolution.

---

## What is in `main`, and what is at the tag

On 2026-10-10 the release candidate of 2.0.0 kept in `main` only what described
the product (`94f7c15`); the Foundation left with the rest of the heritage, which
is kept whole at the tag `archive/heritage-2.0.0-rc1`. From that day the
principles were cited by the code and could not be read beside it.

On 2026-11-15 the owner decided that the core of the principles returns to
`main` and that everything else stays at the tag. A document returns when it is
read or verified; `scripts/ghe_audit.py` measures every citation that leads to a
document `main` does not hold.

In `main`, under `docs/00-foundation/`:

| Document | Subject |
|---|---|
| The-Sustainable-Heritage-Manifesto | The eighteen articles, upstream of the Constitution |
| FDN-0001 | This index |
| FDN-0003 | The Constitution |
| FDN-0004 | The Governed Heritage, and the principles of the Kernel |
| FDN-0007 | The Governed Engineering Cycle |
| FDN-0008 | The Self-Application Principle |
| FDN-0009 | The AI Collaboration Protocol |
| FDN-0010 | The Project Working Invariants |
| FDN-0011 | Contract-Based Engineering |
| FDN-0012 | The Principles Registry |
| FDN-0013 | The Knowledge Acquisition Protocol (Draft, 2026-11-17) |
| ENG-TEST-0001 | Mandatory unit testing |
| ENG-TEST-0002 | The declared execution environment |

## Kept at the tag

By decision of the owner, 2026-11-15, the documents below stay at
`archive/heritage-2.0.0-rc1` and are not brought back to `main`. A citation of
one of them, anywhere in `main`, leads there. This table is the one place that
says so: `scripts/ghe_audit.py` reads it, and a cited document that is neither
in `main` nor in this table is reported.

| Document | Subject | Path at the tag |
|---|---|---|
| FDN-0005 | Project Operating Model | `docs/00-foundation/` |
| FDN-0006 | Project Workspace Operating Model | `docs/00-foundation/` |
| GOV-0001 | Semantic Knowledge Governance | `docs/03-governance/` |
| STD-0001 | Standards README | `docs/02-standards/` |
| STD-0002 | Test Artifact Isolation | `docs/02-standards/testing/` |
| STD-0101 | Writing Rules | `docs/02-standards/documentation/` |
| STD-0200 | Specification Standard | `docs/02-standards/specifications/` |
| OPS-0012 | Dead Code Quarantine | `docs/04-development/` |
| CMP-0001 | Context Bundle Generator | `docs/04-development/context-bundle-generator/` |
| CMP-0012 | Innovation Pipeline | `docs/04-development/innovation-pipeline/` |

`FDN-0005` and `FDN-0006` describe an organisation of the work the project no
longer has. The others govern, or describe, what left `main` on 2026-10-10.

A document due back with a later lot of the reintegration is not listed here:
it stays reported until it returns.

*Version 1.1 ended on a list of seven file names — `Constitution.md`,
`Principles.md`, `Semantic-Core.md`, `Engineering-Method.md` and three others —
none of which was the name of a file in this directory. The table above replaces
it and names what is there.*
