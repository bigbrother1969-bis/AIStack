---
artifact:
  id: ARCH-0002
  title: Kernel Architecture
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-09-23
---

# ARCH-0002 — Kernel Architecture

## Purpose

This document describes the core responsibilities and boundaries of the AIStack Kernel.

## Kernel Responsibility

The Kernel is the deterministic core of the Knowledge Operating System.

It assembles governed capabilities but does not contain domain-specific business logic.

## Core Components

- Kernel Runtime: executes governed operations.
- Kernel Context: aggregates runtime registries.
- Registries: expose governed capabilities.
- Knowledge Providers: collect governed raw observations.

A Knowledge Pipeline is not a component. It is a named sequence of the
components above — provider → observation → runtime catalog → artifact
generator → artifact — with no type, no registry and no `run()` of its own
(`ARCH-0005` § *Contract*).

## Extension Points

- Providers
- Policies
- Catalog Views
- Selection Strategies
- Artifact Generators
- AI Engines

Pipelines are not an extension point, since nothing registers one. A new
pipeline is a new command that chains existing contracts end to end
(`ARCH-0005` § *Current Pipelines*).

*Corrected 2026-09-23, `GOV-0002/OS-063`. Until then § Core Components
listed "Knowledge Pipelines: execute deterministic knowledge flows" and
§ Extension Points listed "Pipelines" — the object `ARCH-0005` retired on
2026-08-28 when `KnowledgePipeline` and `PipelineRegistry` were removed.
`ARCH-0005` and `ARCH-0007` named the discrepancy that day and left its
correction to this document.*

## Boundary

The Kernel shall remain independent of infrastructure technologies, user interfaces, AI models and deployment targets.

Docker, Compose, Ollama and future technologies are integrations behind governed contracts.

## Principle

The Kernel provides structure.

Registered capabilities provide behavior.
