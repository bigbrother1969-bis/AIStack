---
artifact:
  id: CMP-0002-ARCH
  title: Python Packaging Architecture
  type: Component Architecture
  version: 1.0
  status: Published
  owner: Development
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
