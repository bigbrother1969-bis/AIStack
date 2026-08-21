---
artifact:
  id: ARCH-0011
  title: Kernel Registry System
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-07-24
  updated: 2026-08-21
---

# ARCH-0011 — Kernel Registry System

## Status

-   Type: C2 --- Architecture Overview Extension
-   Status: Validated concept --- Pending architecture consolidation

## Purpose

Define how AIStack discovers, describes and governs its internal
capabilities.

The Kernel does not directly know all components. The Kernel relies on
registries that describe available contracts, capabilities and services.

## Core Principle

The Kernel is the library.

The KernelRuntime is the librarian.

The Kernel provides structure, composition and access to knowledge about
available capabilities.

## Kernel Registry System

    Kernel
       |
       v
    Kernel Registry System
       |
       +-- Contract Registry
       +-- Capability Registry
       +-- Service Registry

## Contract Registry

The Contract Registry is the Single Point Of Truth for AIStack
collaboration boundaries.

It describes: - contract identity; - version; - responsibility; -
inputs; - outputs; - guarantees; - compatibility rules.

A contract defines what a component promises. It does not define
implementation.

## Capability Registry

The Capability Registry describes what AIStack can do.

A capability represents an intent.

Examples: - Observe infrastructure - Catalog knowledge - Generate
documentation - Transfer artifacts - Validate transactions

A capability is not a service. It is implemented by one or more
services.

## Service Registry

The Service Registry describes which services provide capabilities.

It contains: - service identity; - lifecycle; - provided capabilities; -
implemented contracts; - dependencies.

## Relationship Model

    Capability
        |
        v
    Service
        |
        v
    Contract

Meaning: - Capability = What AIStack can do - Service = Who performs
it - Contract = How components collaborate

## Registry vs Repository

A Registry describes available elements.

A Repository stores artifacts.

    Registry
      |
      +-- describes knowledge

    Repository
      |
      +-- stores knowledge artifacts

## Self-Onboarding Impact

The Kernel bootstrap process becomes:

    Load Registry Manifest
            |
    Load Contracts
            |
    Discover Capabilities
            |
    Resolve Services
            |
    Build Kernel Context
            |
    Start KernelRuntime

## Architectural Position

This concept supports: - Self-Onboarding; - Knowledge Governance; -
Contract First Architecture; - Explicit Dependencies; - Replaceable
Components; - Portable Knowledge.

This document remains a C2 overview until validated through historical
architecture analysis.
