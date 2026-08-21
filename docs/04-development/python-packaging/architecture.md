---
artifact:
  id: CMP-0002-ARCH
  title: Python Packaging Architecture
  type: Component Architecture
  semantic_type: Knowledge Artifact
  domain: Engineering
  criticality: C1
  confidence: Declared
  version: 1.0
  status: Published
  owner: Development
  created: 2026-07-06
  updated: 2026-07-06
---

# Python Packaging Architecture

## Objective

Define the packaging architecture of AIStack.

## Architecture

    pyproject.toml
            │
            ▼
      src/aistack
            │
            ▼
       CLI entry point
            │
            ▼
         aistack

## Design Rules

- src layout
- Editable installation
- Minimal dependencies
- Portable packaging
