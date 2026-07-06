---
artifact:
  id: STD-0102
  title: Naming Conventions
  type: Documentation Standard
  status: Published
  version: 1.0
  owner: Foundation
  created: 2026-07-06
  updated: 2026-07-06

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

# File Names

Canonical Knowledge Artifacts shall follow the pattern:

```text
<ID>-<Title>.md
```

Examples:

```text
FDN-0003-Constitution.md

STD-0100-Documentation-Standard.md

ADR-0001-Context-Bundle-Generator.md
```

---

# Directory Names

Directories describe domains rather than artifacts.

Examples:

```text
00-foundation/

01-architecture/

02-standards/

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
```

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
