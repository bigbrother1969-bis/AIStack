# Kernel Registries

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
