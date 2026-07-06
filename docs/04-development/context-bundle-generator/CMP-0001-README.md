---
artifact:
  id: CMP-0001
  title: Context Bundle Generator
  type: Component README
  version: 1.0
  status: Published
  owner: Development

lifecycle:
  created: 2026-07-06
  updated: 2026-07-06

relations:
  references:
    - FDN-0005
    - STD-0100
    - STD-0200
---

# Context Bundle Generator

## Purpose

The Context Bundle Generator is the first AIStack component dedicated to the controlled transmission of the Governed Heritage to external reasoning environments.

Its primary purpose is to generate assistant-ready context bundles from canonical Knowledge Artifacts stored in the Git repository.

The generator does not create knowledge.

It creates disposable views of governed knowledge.

---

## Problem

AIStack knowledge is produced across several working conversations, documents and components.

Without a controlled publication mechanism, each working context may progressively diverge from the official Governed Heritage.

This creates risks of:

- inconsistent terminology
- duplicated principles
- outdated assumptions
- undocumented decisions
- fragmented reasoning across specialized assistants

---

## Principle

The Git repository remains the Single Point of Truth.

Context bundles are generated artifacts.

They are used to feed external tools, assistants or documentation systems with a coherent view of the Governed Heritage.

---

## Scope

The first version of the generator produces a ChatGPT Project Source bundle.

This bundle is intended to be uploaded manually into the AIStack ChatGPT project sources.

Future versions may generate bundles for other consumers.

Examples:

- ChatGPT
- Claude
- Gemini
- public documentation
- developer workspaces
- AIStack internal engines

---

## Non-Goals

The Context Bundle Generator does not:

- replace the Git repository
- edit canonical documents
- decide which knowledge is valid
- perform semantic reasoning
- generate new Foundation principles
- synchronize ChatGPT sources automatically

---

## Core Workflow

```text
Git Repository
      ↓
Canonical Knowledge Artifacts
      ↓
Context Bundle Generator
      ↓
Generated Context Bundle
      ↓
ChatGPT Project Sources
      ↓
Specialized Conversations
