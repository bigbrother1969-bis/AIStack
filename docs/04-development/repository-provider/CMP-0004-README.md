---
artifact:
  id: CMP-0004
  title: Repository Knowledge Provider
  type: Component README
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

# CMP-0004 — Repository Knowledge Provider

## Purpose

Observe a source code repository and produce governed Knowledge Artifacts describing its contents.

The Repository Provider is the first concrete Knowledge Provider of the AIStack Knowledge Operating System.

It demonstrates how governed knowledge is extracted from an existing heritage.

## Responsibilities

- Observe a repository.
- Discover Knowledge Artifacts.
- Produce KnowledgeArtifact objects.
- Never modify the repository.
- Remain technology-independent outside repository observation.

## Principle

The Repository Provider observes.

It never interprets business knowledge.

It only exposes governed observations.
