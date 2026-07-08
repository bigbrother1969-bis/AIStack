# AIStack Kernel Architecture Overview

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

- KERNEL-ARCHITECTURE.md: overall Kernel responsibilities and boundaries.
- RUNTIME-ARCHITECTURE.md: Runtime lifecycle, operations and state model.
- PIPELINES.md: Knowledge Pipeline architecture and execution model.
- REGISTRIES.md: governed registries and capability discovery.
- PROVIDERS.md: Knowledge Provider model and responsibilities.
- KNOWLEDGE-FLOW.md: deterministic knowledge flow from observation to governed artifacts.
- AI-RUNTIME.md: AI Engine integration principles.

## Governance

The Kernel documentation is governed knowledge.

It must remain explicit, modular, traceable, portable and independent of any specific AI model or infrastructure provider.

## Principle

The Kernel does not contain domain-specific business logic.

The Kernel assembles governed capabilities.

Domain-specific behavior is provided through registered Providers, Pipelines, Policies, Views, Strategies, Generators and AI Engines.
