---
artifact:
  id: ARCH-0002
  title: Kernel Architecture
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 2.0
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-11-17
---

# ARCH-0002 — Kernel Architecture

## Provenance

Version 1.1 left `main` on 2026-10-10 and is at the tag
`archive/heritage-2.0.0-rc1` under `docs/01-architecture/kernel/`. This version
returns with lot 5 of the reintegration (`ADR-0027` § 5), revised against
`main` at `b10a596`: the list of components and of extension points says what
the code holds, no more. Version 1.1's account of how it was corrected is at
the tag.

## Purpose

This document describes the core responsibilities and boundaries of the AIStack Kernel.

## Kernel Responsibility

The Kernel is the deterministic core of the Knowledge Operating System.

It assembles governed capabilities but does not contain domain-specific business logic.

## Core Components

- **Kernel** (`aistack.kernel.Kernel`): the immutable composition of the
  registries and the services. It builds nothing: composition is done once,
  by `create_kernel()`, which registers what `src/aistack/registrations.yml`
  declares.
- **Kernel Runtime** (`aistack.kernel.runtime.KernelRuntime`): resolves a
  Request to a Task, executes it, produces the execution trace and keeps it
  through a `TraceRepository`. It is the one way a chain runs
  (`ADR-0027` § 10).
- **Registries** (`ARCH-0007`): expose the governed capabilities.
- **Kernel Services** (`aistack.kernel.services.KernelServices`): transport,
  execution (the trace repository) and transactions.
- **Knowledge Providers**: collect governed raw observations.

A knowledge chain is not a component. It is a Task, registered in the Task
registry and executed by the Runtime: provider → observation → catalog →
artifact generator → artifact, with a trace of its execution.

## Extension Points

Extended by a line in `registrations.yml`, never by a change of the Kernel:

- Providers;
- Catalog Views;
- Tasks.

Selection Strategies have a registry, which is empty after bootstrap on
purpose: a strategy takes its identifiers when it is built, so each selection
builds its own.

Policies, Artifact Generators and AI Engines were listed here by version 1.1.
No registry holds them and nothing registers them: a generator or an engine is
built by the Task that uses it. They are not extension points of the Kernel.

## Boundary

The Kernel shall remain independent of infrastructure technologies, user interfaces, AI models and deployment targets.

Docker, Compose, Ollama and future technologies are integrations behind governed contracts.

`scripts/ghe_audit.py` measures it: the Kernel may name a generic mechanism,
never a technology (`ADR-0027` § 7).

## Principle

The Kernel provides structure.

Registered capabilities provide behavior.
