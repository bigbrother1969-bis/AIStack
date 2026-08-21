---
artifact:
  id: ARCH-0002
  title: Kernel Architecture
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
- Knowledge Pipelines: execute deterministic knowledge flows.
- Knowledge Providers: collect governed raw observations.

## Extension Points

- Providers
- Pipelines
- Policies
- Catalog Views
- Selection Strategies
- Artifact Generators
- AI Engines

## Boundary

The Kernel shall remain independent of infrastructure technologies, user interfaces, AI models and deployment targets.

Docker, Compose, Ollama and future technologies are integrations behind governed contracts.

## Principle

The Kernel provides structure.

Registered capabilities provide behavior.
