# AIStack Architecture Principles --- Capability Model Consolidation

## Status

-   Type: Governed Knowledge Consolidation Artifact
-   Domain: Foundation / Architecture
-   Criticality: C1-C3 consolidated reference
-   Purpose: Consolidate validated AIStack architecture principles
-   Status: Proposed update after consistency review

------------------------------------------------------------------------

# C3 --- Fundamental Principles

## C3-01 --- Knowledge is the Primary Asset

The primary asset managed by AIStack is governed knowledge.

Software components, code, documentation, catalogs and generated
artifacts are derived expressions of this knowledge heritage.

------------------------------------------------------------------------

## C3-02 --- AI is a Reasoning Assistant, Never a Source of Truth

AI assists analysis, explanation and reasoning.

AI does not create authoritative knowledge and never replaces evidence,
governance or human validation.

------------------------------------------------------------------------

## C3-03 --- Observation Before Understanding

AIStack must observe reality before interpreting it.

An Observation is a factual representation collected from a digital
ecosystem.

An Observation is not yet Knowledge.

------------------------------------------------------------------------

## C3-04 --- No Information Concept in the Knowledge Model

AIStack deliberately avoids the ambiguous concept of Information.

The governed chain is based on explicit concepts:

Reality → Evidence → Observation → Qualification → Knowledge → Governed
Heritage

------------------------------------------------------------------------

## C3-05 --- Generic Kernel Principle

The Kernel contains stable concepts, composition mechanisms and
governance structures.

Technology-specific behavior belongs outside the Kernel.

------------------------------------------------------------------------

## C3-06 --- Layer Isolation Principle

Each architectural layer only depends on the layer immediately below it.

Higher layers express intent and orchestration.

Lower layers provide capabilities and execution mechanisms.

Cross-layer coupling is forbidden.

------------------------------------------------------------------------

## C3-07 --- Temporary Replace Principle Before Heritage Historization

Before the implementation of the Knowledge Heritage History mechanism,
conflicting knowledge definitions must be managed through a temporary
replace process.

When a new validated principle supersedes an existing principle:

-   the new principle becomes the single active reference;
-   the previous principle must not remain as an active alternative;
-   parallel conflicting definitions are forbidden;
-   the replacement must preserve enough context to explain that a
    previous definition existed and was superseded.

The objective is to preserve a Single Point Of Truth while avoiding
contradictory knowledge states.

This temporary approach applies until AIStack provides native knowledge
historization capabilities allowing:

-   versioning;
-   superseded states;
-   validity periods;
-   replacement reasons;
-   complete lineage between knowledge versions.

Until then:

Current Truth \> Historical Complexity.

------------------------------------------------------------------------

# C2 --- Architecture Principles

## C2-01 --- Request Driven Execution

A Request is the entry point of an execution flow.

A Request identifies the required Task and provides execution context.

------------------------------------------------------------------------

## C2-02 --- Task as Executable Context

A Task is the executable unit resolved from a Request.

A Task does not define technical implementation details.

A Task orchestrates the execution of required capabilities within a
context.

------------------------------------------------------------------------

## C2-03 --- Capability as a Governed Ability

A Capability defines what AIStack is able to do.

A Capability is a stable architectural concept independent from its
implementation.

Capabilities are registered and discoverable.

------------------------------------------------------------------------

## C2-04 --- Capability Composition Principle

A Capability is composed of Actions.

The relationship is:

Capability → Actions

An Action is the smallest atomic execution unit.

------------------------------------------------------------------------

## C2-05 --- Service Provides Capability

Capabilities are provided through governed Services or Providers
implementing the required contracts.

The relationship is:

Service / Provider → Capability → Action

A Provider is not itself a Capability.

------------------------------------------------------------------------

## C2-06 --- Action Execution Principle

Actions perform concrete atomic operations.

Actions may participate in knowledge acquisition flows and may produce
Observations when their purpose is observation or acquisition.

Not every Action produces an Observation.

------------------------------------------------------------------------

## C2-07 --- Observation Belongs to Knowledge Acquisition Flow

Observation is not an execution layer below Action.

Observation belongs to the knowledge acquisition flow:

Reality → Evidence → Observation → Qualification → Knowledge

------------------------------------------------------------------------

## C2-08 --- Provider Observation Principle

Providers acquire or expose governed evidence from digital ecosystems.

Providers do not interpret observations or create knowledge directly.

------------------------------------------------------------------------

## C2-09 --- Registry Governance Principle

Registries govern discoverability.

They describe what exists and how capabilities can be resolved.

Registries do not store knowledge artifacts.

Expected registries include:

-   Contract Registry
-   Task Registry
-   Capability Registry
-   Provider Registry
-   Pipeline Registry
-   Strategy Registries

------------------------------------------------------------------------

## C2-10 --- Registry / Repository Separation

Registries govern discoverability.

Repositories govern storage of artifacts.

Location abstracts the physical placement of artifacts.

------------------------------------------------------------------------

## C2-11 --- Contract First Architecture

Contracts define collaboration boundaries.

Implementations remain replaceable.

------------------------------------------------------------------------

## C2-12 --- Runtime Orchestration Principle

KernelRuntime orchestrates Requests, Tasks, Capabilities and Actions.

KernelRuntime does not replace specialized services or providers.

------------------------------------------------------------------------

# C1 --- Conceptual Models

## C1-01 --- Library Architecture Analogy

AIStack follows the library model:

-   Kernel = Library building
-   KernelRuntime = Librarian
-   KernelServices = Specialized teams
-   Registry = Library catalog of available capabilities
-   Repository = Storage area
-   Location = Shelf location
-   Knowledge Artifact = Book

------------------------------------------------------------------------

## C1-02 --- Capability Model

The capability model is:

Service / Provider

provides

Capability

composed of

Actions

------------------------------------------------------------------------

## C1-03 --- Knowledge Flow Model

Knowledge acquisition follows:

Reality

↓

Evidence Acquisition

↓

Observation

↓

Qualification

↓

Knowledge

↓

Governed Heritage

------------------------------------------------------------------------

# Consistency Review Result

The following ambiguities were removed:

-   Provider is not considered a direct parent layer of Capability.
-   Capability is not considered an execution step.
-   Observation is not considered a lower execution layer after
    Provider.
-   Registry responsibilities are separated from Repository
    responsibilities.
-   Actions are atomic execution units without assuming every Action
    creates Observations.
-   Conflicting active definitions are replaced until native heritage
    historization exists.

Remaining points requiring future ADR confirmation:

1.  Exact boundary between Provider and Service naming.
2.  Exact lifecycle of Actions inside Capabilities.
3.  Exact mapping between Task execution and Capability resolution.

No known contradiction with existing AIStack principles has been
identified.
