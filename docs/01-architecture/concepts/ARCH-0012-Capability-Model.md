---
artifact:
  id: ARCH-0012
  title: Capability Model
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Draft
  owner: Architecture
  created: 2026-07-25
  updated: 2026-09-23
---

# ARCH-0012 — Capability Model

## Status

-   Category: C2 Architecture Principle
-   Source: AIStack-Capability-Model-Principles-Consolidated-v3.md
-   Purpose: Define the capability-oriented execution architecture of
    AIStack

This document is the governed architecture location for Capability Model
principles.

------------------------------------------------------------------------

# Request Driven Execution Principle

A Request is the entry point of an execution flow.

A Request identifies the required Task and provides execution context.

Flow:

``` text
Request
   |
   v
Task
```

A Request does not directly execute technical operations.

------------------------------------------------------------------------

# Task as Executable Context Principle

A Task is the executable context resolved from a Request.

A Task does not define technical implementation details.

A Task orchestrates the execution of required capabilities within a
given context.

Flow:

``` text
Request
   |
   v
Task
   |
   v
Capability
```

------------------------------------------------------------------------

# Capability as a Governed Ability

A Capability defines what AIStack is able to do.

A Capability is a stable architectural concept independent from its
implementation.

A Capability does not execute directly.

It exposes possible Actions.

------------------------------------------------------------------------

# Capability Composition Principle

A Capability is composed of Actions.

``` text
Capability
     |
     v
Actions
```

An Action is the smallest atomic execution unit.

------------------------------------------------------------------------

# Service Provides Capability Principle

A Service or Provider implements one or more Capabilities.

``` text
Service / Provider
        |
        v
Capability
        |
        v
Action
```

Rules:

-   A Provider is not itself a Capability.
-   A Capability represents what AIStack can do.
-   A Service or Provider represents who performs the capability.

------------------------------------------------------------------------

# Action Execution Principle

Actions perform concrete atomic operations.

Actions may participate in knowledge acquisition flows and may produce
Observations when their purpose is observation or acquisition.

Not every Action produces an Observation.

------------------------------------------------------------------------

# Observation Belongs to Knowledge Acquisition Flow

Observation is not an execution layer below Action.

Observation belongs to the knowledge acquisition flow:

``` text
Reality
   |
   v
Evidence
   |
   v
Observation
   |
   v
Qualification
   |
   v
Knowledge
```

Observation and execution are two different architectural dimensions.

------------------------------------------------------------------------

# Provider Observation Principle

Providers are responsible for collecting Observations from external
systems.

Providers do not directly produce governed Knowledge.

Flow:

``` text
Provider
   |
   v
Observation
   |
   v
Knowledge Acquisition Pipeline
```

------------------------------------------------------------------------

# Open Points

The following subjects require future clarification:

-   Exact lifecycle of Actions inside Capabilities.
-   Exact mapping between Task execution and Capability resolution.
-   Detailed orchestration rules inside KernelRuntime.

------------------------------------------------------------------------

# Status, 2026-09-23

**The Capability Composition Principle stands: a Capability is composed of
Actions.** Decided 2026-09-23 by the owner, `GOV-0002/OS-066`. It is a
base principle of this model, alongside `ARC-P-011` (*Capabilities define
what AIStack can do; services provide them*), not an implementation plan.

`ADR-0008` qualified *Action* and *Observation Service* `abandoned` on
2026-08-28 as **stages of the execution chain that decision committed
to**. The chain that was built — Request → Task → Kernel Runtime, with its
`ExecutionTrace` — has no such stages, and nothing in it waits for one.
That qualification is about `ADR-0008`'s implementation. It does not retire
the principle stated here.

On 2026-09-23 no class named `Action` exists. The one capability built,
`TransportCapability` (`aistack.transport`), groups two technology-specific
primitives, `Receiver` and `Writer`. Whether they are its Actions is stated
nowhere. That question belongs to the first item of § *Open Points*, which
stays open.
