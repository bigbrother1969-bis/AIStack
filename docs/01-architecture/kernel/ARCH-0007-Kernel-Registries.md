---
artifact:
  id: ARCH-0007
  title: Kernel Registries
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

# ARCH-0007 — Kernel Registries

## Purpose

This document describes Kernel registries and governed capability discovery.

## Responsibility

Registries expose Kernel capabilities without hardcoding technology-specific behavior into the Runtime.

## Current Registries

- ProviderRegistry: registered Knowledge Providers.
- PipelineRegistry: registered Knowledge Pipelines.
- CatalogViewRegistry: registered Catalog View engines.
- SelectionStrategyRegistry: registered Selection Strategies.

## Discovery Model

Capabilities are registered into the Kernel Context during bootstrap.

Application code requests capabilities from the Kernel Context instead of instantiating implementations directly.

## Principle

The Kernel is extended by registration, not by modification.
