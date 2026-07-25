# AIStack Capability Model - Architecture Principles (C2)

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
