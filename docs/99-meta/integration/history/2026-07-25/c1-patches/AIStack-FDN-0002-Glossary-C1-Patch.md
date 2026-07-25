# AIStack Foundation Glossary --- C1 Patch

## Purpose

Add missing concepts extracted from validated transport artifacts.

Existing concepts must not be duplicated. Observation already exists and
must only be enriched if required.

------------------------------------------------------------------------

# Request

A Request is an expression of an intended operation or objective
submitted to AIStack.

A Request does not directly execute technical operations.

A Request is transformed into an executable context through Task
resolution.

------------------------------------------------------------------------

# Task

A Task is an executable context derived from a Request.

A Task defines the context in which capabilities are resolved and
executed.

A Task does not define implementation details.

------------------------------------------------------------------------

# Capability

A Capability is a governed ability of AIStack.

It defines what AIStack can do independently from implementation
technology.

A Capability is implemented by one or more Services or Providers and
exposes executable Actions.

------------------------------------------------------------------------

# Action

An Action is the smallest executable unit of a Capability.

Actions represent concrete operations performed by AIStack capabilities.

------------------------------------------------------------------------

# KnowledgePackage

A KnowledgePackage is a transport container used to move Knowledge
Artifacts between environments.

A KnowledgePackage is not a Single Point Of Truth.

The repository remains the authoritative source of governed knowledge.

------------------------------------------------------------------------

# Package Manifest

A Package Manifest is the descriptive metadata associated with a
KnowledgePackage.

It identifies package content, origin, version and governance
information.

------------------------------------------------------------------------

# PackagingPolicy

A PackagingPolicy is a governed rule defining how KnowledgePackages are
created, validated and transported.

------------------------------------------------------------------------

# ValidationEngine

A ValidationEngine is a governance component responsible for evaluating
whether a proposed knowledge integration satisfies defined policies and
constraints.

A ValidationEngine does not perform integration.

------------------------------------------------------------------------

# IntegrationEngine

An IntegrationEngine is a governance component responsible for applying
validated knowledge changes.

Validation and integration remain separate responsibilities.

------------------------------------------------------------------------

# Knowledge State

A Knowledge State represents the governance status of a knowledge
element.

Examples:

-   validated knowledge;
-   proposed knowledge;
-   unknown knowledge;
-   conflicting knowledge;
-   rejected knowledge.

------------------------------------------------------------------------

# Governance Proposal

A Governance Proposal is a proposed change generated from analysis or
validation workflows.

A Governance Proposal requires appropriate validation before becoming
governed knowledge.
