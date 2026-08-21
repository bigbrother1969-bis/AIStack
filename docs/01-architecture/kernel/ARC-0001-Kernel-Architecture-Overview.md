---
artifact:
  id: ARC-0001
  title: Kernel Architecture Overview
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

# ARC-0001 — Kernel Architecture Overview

## Purpose

This document is the architectural entry point for the AIStack Kernel documentation.

It explains how the main Kernel architecture documents are organized and how the Kernel components relate to each other.

The Kernel documentation describes how AIStack progressively becomes a Knowledge Operating System (KOS).

## Architecture Map

Knowledge Operating System
  -> Kernel Runtime
  -> Kernel Context
  -> Registries
  -> Knowledge Pipelines
  -> Knowledge Providers
  -> Observations
  -> Runtime Catalogs
  -> Catalog Views
  -> Selection Strategies
  -> Knowledge Policies
  -> Artifact Generators
  -> Governed Knowledge Artifacts
  -> AI Runtime

## Documentation Structure

- ARC-0002 — Kernel Architecture: overall Kernel responsibilities and boundaries.
- ARC-0008 — Kernel Runtime Architecture: Runtime lifecycle, operations and state model.
- ARC-0005 — Knowledge Pipelines: Knowledge Pipeline architecture and execution model.
- ARC-0007 — Kernel Registries: governed registries and capability discovery.
- ARC-0006 — Knowledge Providers: Knowledge Provider model and responsibilities.
- ARC-0004 — Knowledge Flow: deterministic knowledge flow from observation to governed artifacts.
- ARC-0003 — AI Runtime Architecture: AI Engine integration principles.

## Governance

The Kernel documentation is governed knowledge.

It must remain explicit, modular, traceable, portable and independent of any specific AI model or infrastructure provider.

## Principle

The Kernel does not contain domain-specific business logic.

The Kernel assembles governed capabilities.

Domain-specific behavior is provided through registered Providers, Pipelines, Policies, Views, Strategies, Generators and AI Engines.
