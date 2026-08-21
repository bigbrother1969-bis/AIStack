---
artifact:
  id: ARCH-0006
  title: Knowledge Providers
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-08-21
---

# ARCH-0006 — Knowledge Providers

## Purpose

This document describes the Knowledge Provider model.

## Responsibility

A Knowledge Provider collects governed raw observations from an external source.

Providers do not decide, interpret or recommend.

## Current Providers

- DockerProvider: observes the local Docker runtime.
- ComposeProvider: derives Docker Compose project observations from Docker runtime labels.

## Future Providers

- FilesystemProvider
- GitRepositoryProvider
- DocumentationProvider
- RuntimeProvider
- OllamaProvider

## Principle

Providers produce evidence.

The Runtime and governed rules transform evidence into knowledge.
