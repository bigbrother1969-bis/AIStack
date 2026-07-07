# ADR-000X - AIStack Kernel Architecture

## Status

Accepted

## Context

AIStack is evolving from a set of tools into a Knowledge Operating System.

Recent implementation work revealed a stable set of generic concepts: Catalog, Catalog View, Selection, Selection Strategy and Registry.

The more AIStack relies on generic Kernel concepts, the more portable and extensible it becomes.

Technology-specific concepts such as Docker, Syncthing, Linux, Kubernetes or Nextcloud shall remain outside the Kernel.

## Decision

AIStack introduces a technology-independent Kernel.

The Kernel contains only generic governed concepts, contracts, registries and engines.

Technology-specific implementations connect to the Kernel through governed contracts and registries.

The Kernel shall not depend directly on any specific infrastructure technology, provider, cloud, model or synchronization tool.

## Kernel Responsibilities

The Kernel is responsible for:

- defining stable contracts;
- managing registries;
- exposing generic engines;
- orchestrating governed concepts;
- preserving technology independence;
- enabling portability across environments.

## Kernel Structure

The target Kernel structure is:

    kernel/
    ├── contracts/
    ├── registry/
    ├── registries/
    ├── lifecycle/
    ├── discovery/
    ├── dependency/
    └── context/

## Generic Concepts

The Kernel manipulates concepts such as:

- Catalog;
- Catalog View;
- Selection;
- Selection Strategy;
- Registry;
- Policy;
- Renderer;
- Generator;
- Knowledge Artifact.

## External Implementations

External or domain-specific implementations include:

- Docker Providers;
- Filesystem Providers;
- Syncthing workflows;
- Nextcloud integrations;
- Kubernetes adapters;
- domain-specific Catalog Views;
- domain-specific Selection Strategies;
- rendering and generation implementations.

These implementations shall remain replaceable plugins around the Kernel.

## Rationale

The portability of AIStack comes from the genericity of its Kernel, not from Docker or any deployment technology.

Every technology-specific concept moved outside the Kernel increases portability, maintainability and extensibility.

The Kernel shall know contracts and registries, not concrete implementations.

## Consequences

Future components shall first be evaluated against the Kernel boundary.

If a concept is generic, it may belong to the Kernel.

If a concept is technology-specific, it shall remain an implementation registered through a Kernel registry.

ProviderRegistry, GeneratorRegistry, RendererRegistry, PolicyRegistry, PortRegistry and PathRegistry shall follow the same registry pattern.

AIStack development shall continue to favor generic Kernel concepts before technology-specific implementation.
